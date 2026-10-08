"""Fase 1 — baseline CANÔNICO (Parte 13): rompimento Donchian filtrado por ADX,
saída por trailing 3×ATR, estado flat. Roda nos 6 pares com custos e valida pelo gate.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from research.backtester import canonical_positions, simulate
from research.run_phase1_baseline import EXP, SYMBOLS, _print_and_save, evaluate_portfolio
from research.run_reference_backtest import _load

ENTRY_N, ATR_N, ATR_MULT, ADX_N, ADX_MIN, LOTS = 55, 14, 3.0, 14, 25.0, 0.1


def build_trades() -> pd.DataFrame:
    symbols_cfg = yaml.safe_load(Path("config/symbols.yaml").read_text(encoding="utf-8"))["symbols"]
    cost_cfg = yaml.safe_load(Path("config/cost_model.yaml").read_text(encoding="utf-8"))
    spread_model = json.loads((EXP / "spread_model.json").read_text(encoding="utf-8"))
    specs = json.loads((EXP / "broker_specs.json").read_text(encoding="utf-8"))
    frames = []
    for s in SYMBOLS:
        bars = pd.read_parquet(Path("data/bars") / s / "4h.parquet")
        sc, spread_p50 = _load(s, symbols_cfg, spread_model, specs, cost_cfg)
        pos = canonical_positions(bars, entry_n=ENTRY_N, atr_n=ATR_N, atr_mult=ATR_MULT,
                                  adx_n=ADX_N, adx_min=ADX_MIN)
        out = simulate(bars, pos, sc, spread_pips=spread_p50, lots=LOTS)
        df = pd.DataFrame(out["trades"])
        df["symbol"] = s
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    trades = build_trades()
    result = evaluate_portfolio(
        trades, "Donchian canonico (trailing 3ATR + flat + ADX>=25) H4",
        {"entry_n": ENTRY_N, "atr_mult": ATR_MULT, "adx_min": ADX_MIN, "lots": LOTS})
    _print_and_save(result, "phase1_canonical.json")


if __name__ == "__main__":
    main()
