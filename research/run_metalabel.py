"""Fase 2i — meta-labeling sobre o ORB (GER40). Desenho: docs/metalabel_orb.md.

Primário = ORB (baseline default) define lado + níveis. Meta-modelo (ML) decide PEGAR ou não
cada sinal. Predições OUT-OF-SAMPLE via Purged K-Fold + embargo (sem vazamento). Threshold τ
por sweep; DSR deflaciona por (modelos × |grade de τ|). Avaliação final por CPCV na série filtrada.

Gate 2i (pré-registrado): Sharpe líq>0 E PSR>0.95 E CPCV≥60% caminhos+ E DSR>0 E MaxDD-p99
tolerável E bate o baseline com folga (Sharpe≥0.5 E menos trades). Comissão=0 (otimista) até medir.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

from research.costs import SymbolCost
from research.cv import CombinatorialPurgedCV, PurgedKFold, make_label_spans
from research.montecarlo import max_drawdown, mc_distribution
from research.orb import ORBParams, orb_dataset
from research.run_orb_pilot import CAPITAL, _spread_by_hour
from research.validation import deflated_sharpe_ratio, probabilistic_sharpe_ratio

ANN = float(np.sqrt(252))
FEATURES = ["or_width_atr", "dist_vwap_atr", "atr_regime", "minute_of_session",
            "prev_day_ret", "h1_slope_atr", "or_vol_ratio", "dow", "direction"]
TAUS = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]


def _sharpe_pp(r):
    s = r.std(ddof=1)
    return float(r.mean() / s) if s > 0 else 0.0


def _daily(net_by_trade: pd.Series, entry_times: pd.Series, all_days) -> np.ndarray:
    pnl = pd.Series(0.0, index=all_days)
    for v, t in zip(net_by_trade, entry_times):
        pnl[pd.Timestamp(t).normalize()] += v
    return (pnl / CAPITAL).to_numpy()


def _model(kind: str):
    if kind == "gbm":
        return HistGradientBoostingClassifier(max_depth=3, max_iter=150,
                                              learning_rate=0.05, min_samples_leaf=40,
                                              l2_regularization=1.0, random_state=42)
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, C=1.0))


def _oos_proba(ds: pd.DataFrame, kind: str) -> np.ndarray:
    """Probabilidade OUT-OF-SAMPLE por trade via Purged K-Fold + embargo (sem look-ahead)."""
    X = ds[FEATURES].to_numpy(float)
    y = ds["y"].to_numpy(int)
    t1 = make_label_spans(pd.DatetimeIndex(ds["entry_time"]), horizon=1)
    proba = np.full(len(ds), np.nan)
    for tr, te in PurgedKFold(n_splits=6, embargo_pct=0.01).split(t1):
        if y[tr].sum() < 20 or (1 - y[tr]).sum() < 20:  # precisa das duas classes
            proba[te] = y[tr].mean()
            continue
        m = _model(kind).fit(X[tr], y[tr])
        proba[te] = m.predict_proba(X[te])[:, 1]
    return proba


def evaluate(ds: pd.DataFrame, all_days, kind: str) -> dict:
    proba = _oos_proba(ds, kind)
    net = ds["net_usd"].to_numpy()
    ent = ds["entry_time"]
    best = None
    for tau in TAUS:
        take = proba >= tau
        if take.sum() < 100:
            continue
        r = _daily(pd.Series(net[take]), ent[take], all_days)
        sr = _sharpe_pp(r) * ANN
        if best is None or sr > best["sharpe_ann"]:
            best = {"tau": tau, "n_take": int(take.sum()), "take": take,
                    "sharpe_ann": sr, "r": r}
    return best


def run(instrument: str = "GER40", commission: float = 0.0) -> dict:
    cfg = yaml.safe_load(Path("config/instruments_intraday.yaml").read_text("utf-8"))["instruments"]
    c = cfg[instrument]
    bars = pd.read_parquet(Path("data/bars") / c["datafeed_code"] / "15min.parquet")
    sc = SymbolCost(instrument, pip=c["pip"], point=c["point"], contract=c["contract_size"],
                    commission_per_million_usd=commission, swap_long_points=0.0, swap_short_points=0.0)
    ds = orb_dataset(bars, c["session_utc"], sc, _spread_by_hour(c["datafeed_code"]),
                     params=ORBParams(), lots=c["volume_min"]).sort_values("entry_time").reset_index(drop=True)
    all_days = pd.DatetimeIndex(sorted(set(pd.to_datetime(bars["timestamp"]).dt.normalize())))

    # baseline (ORB puro, sem filtro) para comparação
    base_r = _daily(ds["net_usd"], ds["entry_time"], all_days)
    base = {"n_trades": len(ds), "sharpe_ann": round(_sharpe_pp(base_r) * ANN, 3),
            "net_usd": round(float(ds["net_usd"].sum()), 2), "win_rate": round(float(ds["y"].mean()), 3)}

    results = {k: evaluate(ds, all_days, k) for k in ("gbm", "logit")}
    # seleciona o melhor modelo pelo Sharpe OOS filtrado
    kind = max(results, key=lambda k: results[k]["sharpe_ann"] if results[k] else -9)
    b = results[kind]

    r = b["r"]
    psr = probabilistic_sharpe_ratio(r) if r.std() > 0 else 0.0
    # CPCV na série filtrada (distribuição de caminhos)
    t1 = make_label_spans(all_days, horizon=1)
    cv = CombinatorialPurgedCV(n_groups=8, n_test_groups=2)
    oos = np.array([_sharpe_pp(r[te]) for _, te in cv.split(t1)])
    pct_pos = float((oos > 0).mean())
    sr_var = max(float(oos.var(ddof=1)), 1e-9)
    n_trials = len(TAUS) * 2  # τ-grid × 2 modelos
    dsr = deflated_sharpe_ratio(r, sr_variance=sr_var, n_trials=n_trials)
    daily_pnl = r * CAPITAL
    mc = mc_distribution(daily_pnl[daily_pnl != 0], block_size=20, n_sims=2000,
                         rng=np.random.default_rng(42))

    beats = bool(b["sharpe_ann"] >= 0.5 and b["n_take"] < base["n_trades"])
    gate = bool(b["sharpe_ann"] > 0 and psr > 0.95 and pct_pos >= 0.60 and dsr > 0 and beats)
    return {
        "phase": "2i", "instrument": instrument, "commission_per_million": commission,
        "baseline_orb": base,
        "model": kind, "gbm_sharpe": round(results["gbm"]["sharpe_ann"], 3) if results["gbm"] else None,
        "logit_sharpe": round(results["logit"]["sharpe_ann"], 3) if results["logit"] else None,
        "tau": b["tau"], "n_trades_filtered": b["n_take"],
        "sharpe_ann": round(b["sharpe_ann"], 3), "psr": round(psr, 4),
        "cpcv_pct_paths_positive": round(pct_pos, 3), "dsr_deflated": round(dsr, 4),
        "mc_maxdd_p99_usd": round(mc["max_drawdown"]["p99"], 2),
        "beats_baseline": beats, "gate_pass": gate, "verdict": "PASS" if gate else "FAIL",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--instrument", default="GER40")
    p.add_argument("--commission", type=float, default=0.0)
    a = p.parse_args()
    out = run(a.instrument, a.commission)
    Path("experiments/metalabel_2i.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print("WROTE experiments/metalabel_2i.json")


if __name__ == "__main__":
    main()
