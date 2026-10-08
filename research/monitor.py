"""Instrumentação de execução (monitor operacional em tempo real).

Cada etapa da aplicação publica estado em `experiments/monitor/`:
  - status.json   — snapshot atual (etapa, tarefa, progresso, ETA, recursos, fila...)
  - events.jsonl  — log append-only (ts, level, msg, campos estruturados)

Escrita atômica no status (tmp + os.replace) para o servidor nunca ler pela metade.
Sem dados simulados: só reflete o que a aplicação de fato executa.
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil

MONITOR_DIR = Path("experiments/monitor")


class ProgressReporter:
    def __init__(self, run: str, phase: str = "0.4", monitor_dir: Path = MONITOR_DIR):
        self.dir = Path(monitor_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.status_path = self.dir / "status.json"
        self.events_path = self.dir / "events.jsonl"
        self.events_path.write_text("", encoding="utf-8")  # zera log do run
        self._lock = threading.Lock()
        self._t0 = time.monotonic()
        self._proc = psutil.Process()
        psutil.cpu_percent(interval=None)  # prime (1ª leitura é 0)
        self._net0 = psutil.net_io_counters()
        self._net_t = time.monotonic()
        self._stop = threading.Event()
        self.s: dict = {
            "run": run, "phase": phase, "state": "running",
            "step": None, "task": None,
            "current_file": None, "data_source": None, "storage": None,
            "done": 0, "total": 0, "remaining": 0,
            "started_at": self._now(), "updated_at": self._now(),
            "elapsed_s": 0.0, "rate_per_s": 0.0, "eta_s": None,
            "queue": {"pending": [], "running": [], "done": []},
            "counters": {"errors": 0, "warnings": 0, "retries": 0},
            "resources": {}, "poll_interval_s": 1,
        }
        self._write()
        self.log("INFO", f"run iniciado: {run}")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _write(self) -> None:
        self.s["updated_at"] = self._now()
        self.s["elapsed_s"] = round(time.monotonic() - self._t0, 1)
        data = json.dumps(self.s, ensure_ascii=False)
        tmp = self.status_path.with_suffix(".tmp")
        tmp.write_text(data, encoding="utf-8")
        # Windows nega o rename se o servidor está lendo o alvo nesse instante
        # (não é atômico como no POSIX). Retry curto cobre a janela de microssegundos.
        for _ in range(12):
            try:
                os.replace(tmp, self.status_path)
                return
            except PermissionError:
                time.sleep(0.02)
        self.status_path.write_text(data, encoding="utf-8")  # fallback (leitura parcial rara)

    def log(self, level: str, msg: str, **fields) -> None:
        rec = {"ts": self._now(), "level": level, "msg": msg, **fields}
        with self._lock:
            with open(self.events_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if level == "ERROR":
                self.s["counters"]["errors"] += 1
            elif level == "WARNING":
                self.s["counters"]["warnings"] += 1
            self._write()

    def set_step(self, step: str, total: int = 0, task: str | None = None) -> None:
        with self._lock:
            self.s.update(step=step, total=total, done=0, remaining=total)
            if task:
                self.s["task"] = task
            self._write()
        self.log("INFO", f"etapa: {step}", total=total)

    def set_task(self, task: str, current_file: str | None = None,
                 data_source: str | None = None, storage: str | None = None) -> None:
        with self._lock:
            self.s["task"] = task
            for k, v in (("current_file", current_file), ("data_source", data_source),
                         ("storage", storage)):
                if v is not None:
                    self.s[k] = v
            self._write()

    def advance(self, n: int = 1, current_file: str | None = None) -> None:
        with self._lock:
            self.s["done"] += n
            self.s["remaining"] = max(self.s["total"] - self.s["done"], 0)
            if current_file is not None:
                self.s["current_file"] = current_file
            el = time.monotonic() - self._t0
            rate = self.s["done"] / el if el > 0 else 0.0
            self.s["rate_per_s"] = round(rate, 2)
            self.s["eta_s"] = round(self.s["remaining"] / rate, 1) if rate > 0 else None
            self._write()

    def set_queue(self, pending=None, running=None, done=None) -> None:
        with self._lock:
            for k, v in (("pending", pending), ("running", running), ("done", done)):
                if v is not None:
                    self.s["queue"][k] = v
            self._write()

    def retry(self, msg: str, reason: str) -> None:
        with self._lock:
            self.s["counters"]["retries"] += 1
        self.log("WARNING", msg, retry=True, reason=reason)

    def _sample(self) -> dict:
        vm = psutil.virtual_memory()
        du = psutil.disk_usage(str(Path.cwd().anchor or "."))
        net = psutil.net_io_counters()
        t = time.monotonic()
        dt = max(t - self._net_t, 1e-6)
        up = (net.bytes_sent - self._net0.bytes_sent) / dt
        down = (net.bytes_recv - self._net0.bytes_recv) / dt
        self._net0, self._net_t = net, t
        return {
            "cpu_pct": psutil.cpu_percent(interval=None),
            "ram_pct": vm.percent, "ram_used_gb": round(vm.used / 1e9, 2),
            "ram_total_gb": round(vm.total / 1e9, 2),
            "disk_pct": du.percent, "disk_free_gb": round(du.free / 1e9, 1),
            "net_up_kbps": round(up / 1024, 1), "net_down_kbps": round(down / 1024, 1),
            "proc_rss_mb": round(self._proc.memory_info().rss / 1e6, 1),
        }

    def heartbeat(self) -> None:
        with self._lock:
            self.s["resources"] = self._sample()
            self._write()

    def start_heartbeat(self, interval: float = 2.0) -> None:
        def loop():
            while not self._stop.is_set():
                try:
                    self.heartbeat()
                except Exception:  # noqa: BLE001 (heartbeat não pode derrubar o run)
                    pass
                self._stop.wait(interval)
        threading.Thread(target=loop, daemon=True).start()

    def finish(self, state: str = "done") -> None:
        self._stop.set()
        with self._lock:
            self.s["state"] = state
            self.s["current_file"] = None
            self._write()
        self.log("INFO", f"run finalizado: {state}")
