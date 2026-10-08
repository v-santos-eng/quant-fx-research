"""Reconciliação Python <-> MT5 (gate do R-01, Fase 0.4).

Compara os trades do EA de referência (Strategy Tester, CSV) com o backtester Python
rodando o MESMO Donchian sobre as PRÓPRIAS barras H4 do MT5 (puxadas via ponte). Usar
as barras do MT5 isola a lógica do engine do problema de fuso (server-time vs UTC):
se os dois engines são equivalentes, os trades batem barra-a-barra.

Gate pré-registrado: |Δ nº de trades| ≤ 1 e |Δ P&L bruto| ≤ 2%.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
import os
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

from research.backtester import donchian_positions, simulate
from research.costs import SymbolCost

CSV = Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal" / "Common" / "Files" / "reference_ea_trades.csv"
OUT = Path("experiments/reconcile.json")
SYMBOL, ENTRY_N, EXIT_N, LOTS = "EURUSD", 55, 20, 0.1
WIN_START = pd.Timestamp("2023-01-01 00:00")
WIN_END = pd.Timestamp("2025-12-31 00:00")
PIP = 1e-4
# custos zerados: comparamos trades e P&L BRUTO (mecânica do engine, não o custo)
SC = SymbolCost(SYMBOL, pip=PIP, point=1e-5, contract=100_000,
                commission_per_million_usd=0.0, swap_long_points=0.0, swap_short_points=0.0)


def load_ea() -> pd.DataFrame:
    df = pd.read_csv(CSV)
    for c in ("entry_time", "exit_time"):
        df[c] = pd.to_datetime(df[c], format="%Y.%m.%d %H:%M:%S")
    return df


def mt5_bars() -> pd.DataFrame:
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize falhou: {mt5.last_error()}")
    mt5.symbol_select(SYMBOL, True)
    rates = None
    for _ in range(5):  # 1ª chamada costuma disparar o download do histórico
        rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_H4,
                                     datetime(2022, 10, 1), datetime(2026, 1, 1))
        if rates is not None and len(rates):
            break
        time.sleep(2)
    err = mt5.last_error()
    mt5.shutdown()
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"copy_rates vazio: {err}")
    b = pd.DataFrame(rates)
    b["timestamp"] = pd.to_datetime(b["time"], unit="s")  # server time (bate com o CSV do EA)
    return b.rename(columns={"tick_volume": "volume"})[["timestamp", "open", "high", "low", "close", "volume"]]


def gross_pnl(trades: list[dict]) -> float:
    tot = 0.0
    for t in trades:
        d = 1 if t["dir"] > 0 else -1
        tot += (t["exit_price"] - t["entry_price"]) * d / PIP * (PIP * SC.contract) * LOTS
    return round(tot, 2)


def main() -> None:
    ea = load_ea()
    bars = mt5_bars()
    # janela: começa 55 barras antes do 1º bar de 2023 (warmup do canal, posição flat)
    k = int(bars.index[bars["timestamp"] >= WIN_START][0])
    sl = bars.iloc[k - ENTRY_N:].reset_index(drop=True)
    sl = sl[sl["timestamp"] <= WIN_END].reset_index(drop=True)

    pos = donchian_positions(sl, ENTRY_N, EXIT_N)
    py_trades = simulate(sl, pos, SC, spread_pips=0.0, lots=LOTS)["trades"]

    ea_rows = [{"dir": int(r.dir), "entry_time": r.entry_time, "entry_price": float(r.entry_price),
                "exit_time": r.exit_time, "exit_price": float(r.exit_price)}
               for r in ea.itertuples()]

    n_ea, n_py = len(ea_rows), len(py_trades)
    matches = mismatches = 0
    examples = []
    for i in range(min(n_ea, n_py)):
        e, p = ea_rows[i], py_trades[i]
        p_dir = 1 if p["direction"] == "long" else -1
        p_entry = pd.Timestamp(p["entry_time"])
        p_exit = pd.Timestamp(p["exit_time"])
        ok = (e["dir"] == p_dir
              and e["entry_time"] == p_entry and e["exit_time"] == p_exit
              and abs(e["entry_price"] - p["entry_price"]) < 2e-5
              and abs(e["exit_price"] - p["exit_price"]) < 2e-5)
        if ok:
            matches += 1
        else:
            mismatches += 1
            if len(examples) < 8:
                examples.append({"idx": i, "ea": e,
                                 "py": {"dir": p_dir, "entry_time": str(p_entry),
                                        "entry_price": p["entry_price"],
                                        "exit_time": str(p_exit), "exit_price": p["exit_price"]}})

    g_ea = gross_pnl([{"dir": r["dir"], "entry_price": r["entry_price"], "exit_price": r["exit_price"]}
                      for r in ea_rows])
    g_py = gross_pnl([{"dir": 1 if t["direction"] == "long" else -1,
                       "entry_price": t["entry_price"], "exit_price": t["exit_price"]}
                      for t in py_trades])
    pnl_diff_pct = round(abs(g_py - g_ea) / abs(g_ea) * 100, 3) if g_ea else None

    gate_trades = abs(n_ea - n_py) <= 1
    gate_pnl = pnl_diff_pct is not None and pnl_diff_pct <= 2.0
    verdict = "PASS" if (gate_trades and gate_pnl and mismatches == 0) else \
              ("PASS (tolerância)" if (gate_trades and gate_pnl) else "FAIL")

    result = {
        "symbol": SYMBOL, "window": [str(WIN_START), str(WIN_END)],
        "n_trades_ea": n_ea, "n_trades_py": n_py,
        "matches": matches, "mismatches": mismatches,
        "gross_pnl_ea_usd": g_ea, "gross_pnl_py_usd": g_py, "pnl_diff_pct": pnl_diff_pct,
        "gate_trades_ok": gate_trades, "gate_pnl_ok": gate_pnl, "verdict": verdict,
        "mismatch_examples": examples,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "mismatch_examples"},
                     indent=2, ensure_ascii=False, default=str))
    if examples:
        print("\n-- exemplos de divergência --")
        for ex in examples:
            print(ex)


if __name__ == "__main__":
    main()
