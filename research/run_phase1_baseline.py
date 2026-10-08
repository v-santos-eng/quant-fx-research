"""Fase 1 — validação estatística de um baseline no portfólio (protocolo Parte 8).

`evaluate_portfolio(trades, ...)` aplica: Sharpe líquido, PSR, distribuição de Sharpe
via CPCV, Monte Carlo (drawdown p99) e DSR (deflaciona pelo nº de ensaios). Gate:
Sharpe líquido > 0. Reutilizado pelos runners de baseline simples e canônico.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.attempt_registry import AttemptRegistry
from research.cv import CombinatorialPurgedCV, make_label_spans
from research.montecarlo import max_drawdown, mc_distribution
from research.validation import (
    deflated_sharpe_ratio,
    expected_max_sharpe,
    probabilistic_sharpe_ratio,
)

EXP = Path("experiments")
SYMBOLS = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "XAUUSD"]
ANN = float(np.sqrt(252))


def _sharpe_pp(r: np.ndarray) -> float:
    s = r.std(ddof=1)
    return float(r.mean() / s) if s > 0 else 0.0


def evaluate_portfolio(trades: pd.DataFrame, name: str, params: dict) -> dict:
    """Aplica o protocolo de validação a um conjunto de trades do portfólio. Devolve
    o dict de resultado com o veredito do gate (Sharpe líquido anual > 0)."""
    t = trades.copy()
    t["exit_time"] = pd.to_datetime(t["exit_time"])
    t = t.sort_values("exit_time").reset_index(drop=True)

    by_day = t.groupby(t["exit_time"].dt.normalize())["net_usd"].sum()
    idx = pd.date_range(by_day.index.min(), by_day.index.max(), freq="B")
    daily = by_day.reindex(idx, fill_value=0.0)
    r = daily.to_numpy()

    sr_pp = _sharpe_pp(r)
    sr_ann = sr_pp * ANN
    psr = probabilistic_sharpe_ratio(r, sr_benchmark=0.0)

    t1 = make_label_spans(daily.index, horizon=1)
    cv = CombinatorialPurgedCV(n_groups=8, n_test_groups=2)
    fold_sr = np.array([_sharpe_pp(r[test]) for _, test in cv.split(t1)])
    sr_var = max(float(fold_sr.var(ddof=1)), 1e-9)

    mc = mc_distribution(t["net_usd"].to_numpy(), block_size=20, n_sims=2000,
                         rng=np.random.default_rng(42))
    dd_real = max_drawdown(np.cumsum(t["net_usd"].to_numpy()))

    n_trials = AttemptRegistry("experiments/attempts.db").count()
    dsr = deflated_sharpe_ratio(r, sr_variance=sr_var, n_trials=n_trials)

    per_pair = {s: {"n_trades": int((t.get("symbol") == s).sum()),
                    "net_usd": round(float(t.loc[t.get("symbol") == s, "net_usd"].sum()), 2)}
                for s in SYMBOLS}
    gate = bool(sr_ann > 0.0)
    return {
        "phase": "1", "strategy": name, "params": params,
        "n_trades": int(len(t)), "net_total_usd": round(float(t["net_usd"].sum()), 2),
        "sharpe_ann": round(sr_ann, 3), "psr": round(psr, 4),
        "cpcv_sharpe_ann_mean": round(float(fold_sr.mean()) * ANN, 3),
        "cpcv_sharpe_ann_std": round(float(fold_sr.std(ddof=1)) * ANN, 3),
        "cpcv_pct_paths_positive": round(float((fold_sr > 0).mean()), 3),
        "mc_maxdd_p50": round(mc["max_drawdown"]["p50"], 2),
        "mc_maxdd_p99": round(mc["max_drawdown"]["p99"], 2),
        "realized_maxdd_usd": round(dd_real, 2),
        "dsr": round(dsr, 4),
        "sr_star_ann": round(expected_max_sharpe(sr_var, n_trials) * ANN, 3),
        "n_trials": n_trials, "per_pair": per_pair,
        "gate_sharpe_gt_0": gate, "verdict": "PASS" if gate else "FAIL",
    }


def _print_and_save(result: dict, out_name: str) -> None:
    (EXP / out_name).write_text(json.dumps(result, indent=2, ensure_ascii=False, default=float),
                                encoding="utf-8")
    AttemptRegistry("experiments/attempts.db").log(
        phase="1", name=result["strategy"], config_hash="", params=result["params"],
        result=result, notes="Fase 1: baseline validado (Sharpe/PSR/CPCV/MC/DSR)")
    print(json.dumps({k: v for k, v in result.items() if k != "per_pair"},
                     indent=2, ensure_ascii=False, default=float))
    print("por par:", result["per_pair"])


def main() -> None:
    blotters = []
    for s in SYMBOLS:
        b = pd.read_parquet(EXP / f"blotter_{s}.parquet")
        b["symbol"] = s
        blotters.append(b)
    trades = pd.concat(blotters, ignore_index=True)
    result = evaluate_portfolio(trades, "Donchian 55/20 H4 portfolio (baseline simples)",
                                {"entry_n": 55, "exit_n": 20, "lots": 0.1})
    _print_and_save(result, "phase1_baseline.json")


if __name__ == "__main__":
    main()
