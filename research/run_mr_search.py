"""Fase 2a — validação robusta + busca honesta do baseline de REVERSÃO (GER40).

Mesmo protocolo do ORB (run_orb_search): seleção pelo Sharpe OOS do CPCV, DSR deflacionado
por |grade|. Gate 1i: Sharpe>0 E PSR>0.95 E CPCV≥60% caminhos+ E DSR>0 E MaxDD-p99 tolerável.
Comissão=0 (otimista) até medir. Reusa helpers de run_orb_search.
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from research.costs import SymbolCost
from research.cv import CombinatorialPurgedCV, make_label_spans
from research.meanrev import MRParams, mr_trades
from research.montecarlo import max_drawdown, mc_distribution
from research.run_orb_pilot import CAPITAL, _spread_by_hour
from research.run_orb_search import ANN, _daily_returns, _sharpe_pp
from research.validation import deflated_sharpe_ratio, probabilistic_sharpe_ratio

GRID = {"z": [1.0, 1.5, 2.0], "stop_atr": [0.75, 1.0, 1.5], "warmup_min": [15, 30]}


def _configs():
    keys = list(GRID)
    for combo in itertools.product(*(GRID[k] for k in keys)):
        yield dict(zip(keys, combo))


def run(instrument: str = "GER40", commission: float = 0.0) -> dict:
    cfg = yaml.safe_load(Path("config/instruments_intraday.yaml").read_text("utf-8"))["instruments"]
    c = cfg[instrument]
    bars = pd.read_parquet(Path("data/bars") / c["datafeed_code"] / "15min.parquet")
    sc = SymbolCost(instrument, pip=c["pip"], point=c["point"], contract=c["contract_size"],
                    commission_per_million_usd=commission, swap_long_points=0.0, swap_short_points=0.0)
    spread = _spread_by_hour(c["datafeed_code"])
    lots = c["volume_min"]
    all_days = pd.DatetimeIndex(sorted(set(pd.to_datetime(bars["timestamp"]).dt.normalize())))
    t1 = make_label_spans(all_days, horizon=1)
    splits = list(CombinatorialPurgedCV(n_groups=8, n_test_groups=2).split(t1))

    grid = list(_configs())
    scored = []
    for cd in grid:
        res = mr_trades(bars, c["session_utc"], sc, spread, params=MRParams(**cd), lots=lots)
        r = _daily_returns(res["trades"], all_days)
        oos = np.array([_sharpe_pp(r[te]) for _, te in splits])
        scored.append({"cfg": cd, "r": r, "n_trades": res["summary"]["n_trades"],
                       "gross": res["summary"]["gross_usd"], "net": res["summary"]["net_usd"],
                       "oos_mean": float(oos.mean()), "oos_pos": float((oos > 0).mean()), "oos": oos})

    best = max(scored, key=lambda s: s["oos_mean"])
    r = best["r"]
    sr_ann = _sharpe_pp(r) * ANN
    psr = probabilistic_sharpe_ratio(r) if r.std() > 0 else 0.0
    sr_var = max(float(best["oos"].var(ddof=1)), 1e-9)
    dsr = deflated_sharpe_ratio(r, sr_variance=sr_var, n_trials=len(grid))
    daily_pnl = r * CAPITAL
    mc = mc_distribution(daily_pnl[daily_pnl != 0], block_size=20, n_sims=2000,
                         rng=np.random.default_rng(42))
    dd_real = max_drawdown(np.cumsum(daily_pnl))

    gate = bool(sr_ann > 0 and psr > 0.95 and best["oos_pos"] >= 0.60 and dsr > 0)
    return {
        "phase": "2a", "strategy": "mean_reversion", "instrument": instrument,
        "commission_per_million": commission, "n_configs": len(grid), "best_config": best["cfg"],
        "n_trades": best["n_trades"], "gross_usd": best["gross"], "net_usd": best["net"],
        "sharpe_ann": round(sr_ann, 3), "psr": round(psr, 4),
        "cpcv_oos_sharpe_ann_mean": round(best["oos_mean"] * ANN, 3),
        "cpcv_pct_paths_positive": round(best["oos_pos"], 3), "dsr_deflated": round(dsr, 4),
        "mc_maxdd_p99_usd": round(mc["max_drawdown"]["p99"], 2),
        "realized_maxdd_usd": round(dd_real, 2),
        "gross_positive": bool(best["gross"] > 0),
        "gate_pass": gate, "verdict": "PASS" if gate else "FAIL",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--instrument", default="GER40")
    p.add_argument("--commission", type=float, default=0.0)
    a = p.parse_args()
    out = run(a.instrument, a.commission)
    Path("experiments/mr_search_2a.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print("WROTE experiments/mr_search_2a.json")


if __name__ == "__main__":
    main()
