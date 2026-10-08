"""Coletor de spread ao vivo da Dukascopy — calibra/confirma o NÍVEL do spread do
broker por par×hora (a FORMA vem do histórico). Append em CSV, robusto a desconexão.

Limitação: rodando como processo de sessão, coleta só enquanto a sessão estiver
aberta. Para uma semana contínua garantida, agendar localmente (Windows Task Scheduler).
"""
from __future__ import annotations

import csv
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5

from research.mt5_client import SYMBOLS, live_spread_points

OUT = Path("experiments/live_spread_samples.csv")
INTERVAL_S = 60
MAX_DAYS = 7


def _connected() -> bool:
    ti = mt5.terminal_info()
    return bool(ti and ti.connected)


def main() -> None:
    end = datetime.now(timezone.utc) + timedelta(days=MAX_DAYS)
    new = not OUT.exists()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    mt5.initialize()
    n = 0
    with open(OUT, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["utc", "symbol", "spread_points"])
        while datetime.now(timezone.utc) < end:
            try:
                if not _connected():
                    mt5.shutdown()
                    mt5.initialize()
                now = datetime.now(timezone.utc).isoformat()
                for s in SYMBOLS:
                    sp = live_spread_points(s)
                    if sp is not None:
                        w.writerow([now, s, sp])
                        n += 1
                f.flush()
            except Exception as e:  # noqa: BLE001 (coletor não pode morrer por um erro)
                print(f"erro amostra: {e}", flush=True)
                mt5.shutdown()
                mt5.initialize()
            time.sleep(INTERVAL_S)
    mt5.shutdown()
    print(f"FIM coletor: {n} amostras", flush=True)


if __name__ == "__main__":
    main()
