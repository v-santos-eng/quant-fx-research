"""Downloader resumável de ticks Dukascopy (Fase 0.2). Idempotente por dia.

Estratégia de robustez (prioridade nº 1):
  - Um Parquet por dia:  data/dukascopy/{SYMBOL}/{YYYY}/{MM}/{DD}.parquet
  - Resumável: se o arquivo do dia existe, pula (retomada após interrupção).
  - Falha de rede após retries => o DIA falha ALTO e NÃO é escrito, para ser
    reprocessado depois (nunca grava dia parcial: um buraco de feed viraria gap falso).
  - 404 => hora legitimamente sem dado (fim de semana/feriado) => vazio, sem erro.
  - Sábado é pulado (mercado fechado); domingo é mantido (ticks no fim do dia).
  - Manifesto CSV audita cada dia (status, n_ticks, sha256).

Uso:
  python -m research.download_dukascopy --smoke
  python -m research.download_dukascopy --start 2010-01-01 --end 2026-07-21
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from research.acquisition import bi5_decode, fetch_day_raw, write_parquet_versioned

SYMBOLS = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "XAUUSD"]
DATA_ROOT = Path("data/dukascopy")
MANIFEST = DATA_ROOT / "_manifest.csv"
# Concorrência global = handshakes TLS simultâneos ao proxy de inspeção SSL desta
# rede. Cada dia = 1 conexão reusada (keep-alive) p/ 24 horas. O proxy custa ~9s/
# handshake e engasga em paralelo alto (32 estourava timeout); 10 é o equilíbrio.
WORKERS = 10


def download_day(symbol: str, day: date, out_root: Path = DATA_ROOT) -> tuple[str, int, str]:
    """Baixa um dia (24 horas, conexão TLS reusada). Retorna (status, n_ticks, sha256).

    status: ok|skip|empty|error. A concorrência é global (nível run), não aqui.
    """
    out_dir = out_root / symbol / f"{day.year:04d}" / f"{day.month:02d}"
    out_path = out_dir / f"{day.day:02d}.parquet"
    if out_path.exists():
        return "skip", 0, ""
    try:
        raw_by_hour = fetch_day_raw(symbol, day)
    except RuntimeError as e:
        print(f"  ERRO {symbol} {day}: {e}", flush=True)
        return "error", 0, ""
    frames = []
    for h, raw in raw_by_hour.items():
        hs = datetime(day.year, day.month, day.day, h, tzinfo=timezone.utc)
        df = bi5_decode(raw, symbol, hs)
        if len(df):
            frames.append(df)
    if not frames:
        return "empty", 0, ""  # dia sem dado (fim de semana): não escreve arquivo
    full = (pd.concat(frames, ignore_index=True)
            .sort_values("timestamp").reset_index(drop=True))
    _, digest = write_parquet_versioned(full, out_dir, f"{day.day:02d}")
    return "ok", len(full), digest


def _iter_days(start: date, end: date):
    d = start
    while d <= end:
        if d.weekday() != 5:  # pula sábado (5); mercado fechado
            yield d
        d += timedelta(days=1)


def _append_manifest(rows: list[dict]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    new = not MANIFEST.exists()
    with open(MANIFEST, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["utc_logged", "symbol", "day", "status",
                                          "n_ticks", "sha256"])
        if new:
            w.writeheader()
        w.writerows(rows)


def run(symbols: list[str], start: date, end: date, workers: int = WORKERS,
        rep=None) -> None:
    tasks = [(sym, day) for sym in symbols for day in _iter_days(start, end)]
    total = len(tasks)
    print(f"=== {len(symbols)} pares, {start}..{end}, {total:,} dias-tarefa, {workers} workers ===",
          flush=True)
    if rep is not None:
        rep.set_step(f"Download ticks {start}..{end}", total=total,
                     task=f"{len(symbols)} instrumentos · {workers} conexões")
        rep.set_queue(pending=list(symbols), running=[], done=[])
        rep.start_heartbeat(2.0)
    done_syms: set[str] = set()
    t0 = time.monotonic()
    n_done = n_ticks = n_err = 0
    buffer: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(download_day, sym, day): (sym, day) for sym, day in tasks}
        for fut in as_completed(futs):
            sym, day = futs[fut]
            status, ticks, digest = fut.result()
            n_ticks += ticks
            n_err += status == "error"
            n_done += 1
            if status in ("ok", "error"):
                buffer.append({"utc_logged": datetime.now(timezone.utc).isoformat(),
                               "symbol": sym, "day": day.isoformat(),
                               "status": status, "n_ticks": ticks, "sha256": digest})
            if rep is not None:
                rep.advance(1, current_file=f"{sym} {day.isoformat()}")
                rep.s["task"] = f"{n_ticks:,} ticks · {n_err} erros · último: {sym} {day}"
                if status == "error":
                    rep.log("ERROR", f"dia falhou: {sym} {day}")
                if sym not in done_syms and day >= end - timedelta(days=6):
                    done_syms.add(sym)
                    rep.set_queue(pending=[s for s in symbols if s not in done_syms],
                                  done=sorted(done_syms))
            if n_done % 500 == 0:
                _append_manifest(buffer); buffer = []
                rate = n_done / max(time.monotonic() - t0, 1e-9)
                eta_h = (total - n_done) / max(rate, 1e-9) / 3600
                print(f"  {n_done:,}/{total:,} dias | {n_ticks:,} ticks | {n_err} erros "
                      f"| {rate:.1f} dias/s | ETA {eta_h:.1f}h", flush=True)
    _append_manifest(buffer)
    print(f"=== FIM: {n_done:,} dias, {n_ticks:,} ticks, {n_err} erros ===", flush=True)
    if rep is not None:
        rep.set_queue(pending=[], done=sorted(set(symbols)))
        rep.finish("done")


def _smoke() -> int:
    """Valida contra dado real de 1 dia (EURUSD) antes de comprometer horas."""
    day = date(2023, 6, 1)
    print(f"SMOKE EURUSD {day} ...", flush=True)
    status, ticks, digest = download_day("EURUSD", day)
    print(f"status={status} n_ticks={ticks} sha256={digest[:16]}", flush=True)
    if status != "ok" or ticks == 0:
        print("SMOKE FALHOU", flush=True)
        return 1
    df = pd.read_parquet(DATA_ROOT / "EURUSD" / "2023" / "06" / "01.parquet")
    print(df.head(3).to_string(), flush=True)
    lo, hi = df["bid"].min(), df["ask"].max()
    ok = 0.9 < lo < 1.3 and 0.9 < hi < 1.3  # EURUSD ~1.07 em 2023 => valida POINT_VALUE
    print(f"faixa de preço [{lo:.5f}, {hi:.5f}] -> {'OK' if ok else 'SUSPEITA'}", flush=True)
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--symbols", nargs="+", default=SYMBOLS)
    p.add_argument("--start", type=lambda s: date.fromisoformat(s), default=date(2010, 1, 1))
    p.add_argument("--end", type=lambda s: date.fromisoformat(s), default=date.today())
    p.add_argument("--monitor", action="store_true", help="publica progresso no monitor 8777")
    a = p.parse_args()
    if a.smoke:
        return _smoke()
    rep = None
    if a.monitor:
        from research.monitor import ProgressReporter
        rep = ProgressReporter(run="download_ticks_intraday_cfd", phase="0i")
    run(a.symbols, a.start, a.end, rep=rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
