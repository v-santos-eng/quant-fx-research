"""Relatório de qualidade do dataset (gate da Fase 0.2). Streaming por arquivo
(um Parquet = um dia), agregando por par sem carregar tudo na memória.

Cobertura = dias presentes / dias úteis esperados (exclui sábado; domingo conta,
pois há ticks no fim do dia). Integridade = quotes cruzados, preços não-positivos,
timestamps duplicados, dias com buraco intradiário > 30min.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from research.attempt_registry import AttemptRegistry
from research.reproducibility import capture_environment
from research.sanity import detect_gaps

DATA_ROOT = Path("data/dukascopy")
OUT = Path("experiments/quality_report_0_2.json")
SYMBOLS = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "XAUUSD"]
GAP = pd.Timedelta("30min")


def _expected_weekdays(d0: date, d1: date) -> int:
    n, d = 0, d0
    while d <= d1:
        if d.weekday() != 5:  # exclui sábado
            n += 1
        d += timedelta(days=1)
    return n


def report_symbol(symbol: str) -> dict:
    files = sorted((DATA_ROOT / symbol).rglob("*.parquet"))
    agg = {"symbol": symbol, "days_present": len(files), "n_ticks": 0, "n_crossed": 0,
           "n_nonpositive": 0, "n_dup": 0, "n_gap_days": 0, "n_gaps": 0,
           "first": None, "last": None}
    for i, f in enumerate(files):
        df = pd.read_parquet(f)
        if not len(df):
            continue
        bid, ask = df["bid"].to_numpy(), df["ask"].to_numpy()
        ts = df["timestamp"]
        agg["n_ticks"] += len(df)
        agg["n_crossed"] += int((bid > ask).sum())
        agg["n_nonpositive"] += int(((bid <= 0) | (ask <= 0)).sum())
        agg["n_dup"] += int(ts.duplicated().sum())
        g = len(detect_gaps(df, GAP))
        if g:
            agg["n_gap_days"] += 1
            agg["n_gaps"] += g
        lo, hi = str(ts.min()), str(ts.max())
        agg["first"] = lo if agg["first"] is None else min(agg["first"], lo)
        agg["last"] = hi if agg["last"] is None else max(agg["last"], hi)
        if (i + 1) % 2000 == 0:
            print(f"  {symbol}: {i + 1}/{len(files)}", flush=True)
    if files and agg["first"]:
        d0 = date.fromisoformat(agg["first"][:10])
        d1 = date.fromisoformat(agg["last"][:10])
        exp = _expected_weekdays(d0, d1)
        agg["expected_weekdays"] = exp
        agg["coverage_ratio"] = round(agg["days_present"] / exp, 4) if exp else None
    return agg


def main(symbols: list[str] | None = None, out: Path = OUT, phase: str = "0.2") -> None:
    symbols = symbols or SYMBOLS
    print(f"=== Relatório de qualidade fase {phase} ({len(symbols)} instrumentos) ===", flush=True)
    reports = [report_symbol(s) for s in symbols]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"WROTE {out}", flush=True)
    for r in reports:
        print(f"{r['symbol']}: dias={r['days_present']} cov={r.get('coverage_ratio')} "
              f"ticks={r['n_ticks']:,} cross={r['n_crossed']} nonpos={r['n_nonpositive']} "
              f"dup={r['n_dup']} gap_days={r['n_gap_days']}", flush=True)
    AttemptRegistry("experiments/attempts.db").log(
        phase=phase, name="quality_report", config_hash="",
        params={"symbols": symbols, "gap": str(GAP), "env": capture_environment()},
        result={"per_symbol": reports},
        notes=f"relatório de qualidade do dataset Dukascopy ({phase})",
    )
    print("LOGGED attempt", flush=True)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--symbols", nargs="+", default=None)
    p.add_argument("--out", type=Path, default=OUT)
    p.add_argument("--phase", default="0.2")
    a = p.parse_args()
    main(a.symbols, a.out, a.phase)
