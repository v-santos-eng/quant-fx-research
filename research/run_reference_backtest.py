"""Backtest de referência (Donchian breakout H4) sobre os 6 pares, com o modelo de
custo real, instrumentado no monitor. Produz blotter + resumo — base da reconciliação
Python↔MT5 (R-01). NÃO é o sinal final (isso é a Fase 1); é instrumento de validação.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import yaml

from research.attempt_registry import AttemptRegistry
from research.backtester import donchian_positions, simulate
from research.costs import SymbolCost
from research.monitor import ProgressReporter

BARS = Path("data/bars")
EXP = Path("experiments")
SYMBOLS = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "XAUUSD"]
ENTRY_N, EXIT_N, LOTS = 55, 20, 0.1


def _load(sym, symbols_cfg, spread_model, specs, cost_cfg):
    c = symbols_cfg[sym]
    is_metal = sym == "XAUUSD"
    tier = cost_cfg["commission"]["assumed_tier"]
    comm = cost_cfg["commission"]["tiers_usd_per_million"]["metals" if is_metal else "fx"][tier]
    sp = specs["symbols"][sym]
    spread_p50 = next(m for m in spread_model if m["symbol"] == sym)["overall"]["p50"]
    sc = SymbolCost(sym, pip=c["pip"], point=10 ** (-c["digits"]), contract=c["contract"],
                    commission_per_million_usd=comm,
                    swap_long_points=sp["swap_long"], swap_short_points=sp["swap_short"])
    return sc, spread_p50


def main() -> None:
    rep = ProgressReporter(run="reference_backtest_donchian_h4", phase="0.4")
    rep.start_heartbeat(interval=1.5)
    symbols_cfg = yaml.safe_load(Path("config/symbols.yaml").read_text(encoding="utf-8"))["symbols"]
    cost_cfg = yaml.safe_load(Path("config/cost_model.yaml").read_text(encoding="utf-8"))
    spread_model = json.loads((EXP / "spread_model.json").read_text(encoding="utf-8"))
    specs = json.loads((EXP / "broker_specs.json").read_text(encoding="utf-8"))

    total = sum(pq.ParquetFile(BARS / s / "4h.parquet").metadata.num_rows for s in SYMBOLS)
    rep.set_step("Backtest de referência Donchian H4 (6 pares)", total=total)
    results, done = {}, []
    try:
        for sym in SYMBOLS:
            rep.set_queue(pending=[s for s in SYMBOLS if s not in done and s != sym],
                          running=[sym], done=done)
            bars = pd.read_parquet(BARS / sym / "4h.parquet")
            sc, spread_p50 = _load(sym, symbols_cfg, spread_model, specs, cost_cfg)
            rep.set_task(f"backtest {sym} — {len(bars):,} barras H4 · spread {spread_p50} pip",
                         data_source=str(BARS / sym / "4h.parquet"),
                         storage=str(EXP / f"blotter_{sym}.parquet"))
            pos = donchian_positions(bars, entry_n=ENTRY_N, exit_n=EXIT_N)
            out = simulate(bars, pos, sc, spread_pips=spread_p50, lots=LOTS, reporter=rep)
            results[sym] = out["summary"]
            pd.DataFrame(out["trades"]).to_parquet(EXP / f"blotter_{sym}.parquet", index=False)
            s = out["summary"]
            rep.log("INFO", f"{sym}: {s['n_trades']} trades · net ${s['net_usd']} · "
                    f"DD ${s['max_drawdown_usd']} · win {s['win_rate']}", **s)
            done.append(sym)
        rep.set_queue(pending=[], running=[], done=done)
        (EXP / "reference_backtest.json").write_text(
            json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        AttemptRegistry("experiments/attempts.db").log(
            phase="0.4", name="reference_backtest_donchian_h4", config_hash="",
            params={"entry_n": ENTRY_N, "exit_n": EXIT_N, "lots": LOTS},
            result=results, notes="baseline Donchian H4 com custos, pré-reconciliação MT5")
        rep.finish("done")
        for s, r in results.items():
            print(f"{s}: {r['n_trades']} trades, net ${r['net_usd']}, DD ${r['max_drawdown_usd']}",
                  flush=True)
    except Exception as e:  # noqa: BLE001
        rep.log("ERROR", f"backtest abortado: {e}")
        rep.finish("error")
        raise


if __name__ == "__main__":
    main()
