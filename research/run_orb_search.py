"""Fase 1i — validação robusta + busca HONESTA de parâmetros do ORB (GER40).

Protocolo anti-p-hacking (López de Prado):
  - Cada config é avaliada pelo Sharpe OUT-OF-SAMPLE dos folds do CPCV (não full-sample).
  - Seleciona a config com melhor Sharpe OOS médio no CPCV.
  - O DSR deflaciona pelo Nº DE CONFIGS testadas (n_trials = |grade|) — corrige o viés
    de escolher o melhor de muitas tentativas. Um Sharpe alto que não sobrevive à
    deflação é ruído de data-mining.
Gate 1i (pré-registrado): Sharpe líq>0 E PSR>0.95 E CPCV≥60% caminhos+ E DSR>0.
Comissão parametrizada (0 = spread-only, otimista) até medir a real do CFD.
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from research.cv import CombinatorialPurgedCV, make_label_spans
from research.montecarlo import max_drawdown, mc_distribution
from research.orb import ORBParams, orb_trades
from research.run_orb_pilot import CAPITAL, _spread_by_hour
from research.costs import SymbolCost
from research.validation import deflated_sharpe_ratio, probabilistic_sharpe_ratio

ANN = float(np.sqrt(252))
GRID = {
    "or_min": [15, 30, 60],
    "atr_mult": [0.75, 1.0, 1.5],
    "r_mult": [1.5, 2.0, 3.0],
    "k_range": [0.3, 0.5, 0.8],
}


def _sharpe_pp(r: np.ndarray) -> float:
    s = r.std(ddof=1)
    return float(r.mean() / s) if s > 0 else 0.0


def _daily_returns(trades: list[dict], all_days: pd.DatetimeIndex) -> np.ndarray:
    pnl = pd.Series(0.0, index=all_days)
    for t in trades:
        pnl[pd.Timestamp(t["entry_time"]).normalize()] += t["net_usd"]
    return (pnl / CAPITAL).to_numpy()


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
    cv = CombinatorialPurgedCV(n_groups=8, n_test_groups=2)
    splits = list(cv.split(t1))

    grid = list(_configs())
    scored = []
    for cd in grid:
        res = orb_trades(bars, c["session_utc"], sc, spread,
                         params=ORBParams(**cd), lots=lots)
        r = _daily_returns(res["trades"], all_days)
        oos = np.array([_sharpe_pp(r[test]) for _, test in splits])  # Sharpe OOS por caminho
        scored.append({"cfg": cd, "r": r, "n_trades": res["summary"]["n_trades"],
                       "gross": res["summary"]["gross_usd"], "net": res["summary"]["net_usd"],
                       "oos_mean": float(oos.mean()), "oos_pos": float((oos > 0).mean()),
                       "oos": oos})

    best = max(scored, key=lambda s: s["oos_mean"])          # seleção OOS (não full-sample)
    r = best["r"]
    sr_ann = _sharpe_pp(r) * ANN
    psr = probabilistic_sharpe_ratio(r) if r.std() > 0 else 0.0
    sr_var = max(float(best["oos"].var(ddof=1)), 1e-9)
    dsr = deflated_sharpe_ratio(r, sr_variance=sr_var, n_trials=len(grid))  # deflaciona por |grade|
    # Monte Carlo de drawdown sobre a série diária da melhor config
    daily_pnl = r * CAPITAL
    mc = mc_distribution(daily_pnl[daily_pnl != 0], block_size=20, n_sims=2000,
                         rng=np.random.default_rng(42))
    dd_real = max_drawdown(np.cumsum(daily_pnl))

    gate = bool(sr_ann > 0 and psr > 0.95 and best["oos_pos"] >= 0.60 and dsr > 0)
    out = {
        "phase": "1i", "instrument": instrument, "commission_per_million": commission,
        "n_configs": len(grid), "best_config": best["cfg"],
        "n_trades": best["n_trades"], "gross_usd": best["gross"], "net_usd": best["net"],
        "sharpe_ann": round(sr_ann, 3), "psr": round(psr, 4),
        "cpcv_oos_sharpe_ann_mean": round(best["oos_mean"] * ANN, 3),
        "cpcv_pct_paths_positive": round(best["oos_pos"], 3),
        "dsr_deflated": round(dsr, 4),
        "mc_maxdd_p99_usd": round(mc["max_drawdown"]["p99"], 2),
        "realized_maxdd_usd": round(dd_real, 2),
        "gate_pass": gate, "verdict": "PASS" if gate else "FAIL",
    }
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--instrument", default="GER40")
    p.add_argument("--commission", type=float, default=0.0)
    a = p.parse_args()
    out = run(a.instrument, a.commission)
    Path("experiments/orb_search_1i.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print("WROTE experiments/orb_search_1i.json")


if __name__ == "__main__":
    main()
