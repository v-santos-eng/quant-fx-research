"""Fase 1d — baseline TSMOM D1 cross-asset (Part 13 do design doc) pelo gate.

Uma config fiel, SEM otimização (como a Phase 1 do doc manda). Custos medidos: spread par×hora
(p50), comissão ECN, e SWAP por ativo (o custo overnight central). Gate do doc: net Sharpe > 0,3
E positivo em ≥3/5 blocos temporais E net ≥ 60% do gross E sobrevive a swap ×2. Também reporta
o gate estatístico do projeto (PSR/CPCV/DSR/MC).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from research.attempt_registry import AttemptRegistry
from research.costs import _base_is_usd
from research.cv import CombinatorialPurgedCV, make_label_spans
from research.montecarlo import max_drawdown, mc_distribution
from research.tsmom import instrument_pnl, portfolio, resample_d1
from research.validation import deflated_sharpe_ratio, probabilistic_sharpe_ratio

ANN = float(np.sqrt(252))
# universo dos 8 do doc: nome -> (pasta de barras, é CFD?)
UNIV = {"EURUSD": ("EURUSD", False), "USDJPY": ("USDJPY", False), "GBPUSD": ("GBPUSD", False),
        "AUDUSD": ("AUDUSD", False), "USDCAD": ("USDCAD", False), "XAUUSD": ("XAUUSD", False),
        "US500": ("USA500IDXUSD", True), "US100": ("USATECHIDXUSD", True)}
FX_COMM_RT = 35.0 / 1e6 * 2      # $35/M por lado, round-trip
GOLD_COMM_RT = 52.5 / 1e6 * 2


def _sharpe(r: np.ndarray) -> float:
    s = r.std(ddof=1)
    return float(r.mean() / s * ANN) if s > 0 else 0.0


def _spread_models() -> dict:
    fx = {m["symbol"]: m for m in json.loads(Path("experiments/spread_model.json").read_text())}
    cfd = {m["symbol"]: m for m in
           json.loads(Path("experiments/spread_model_intraday.json").read_text())}
    return {**fx, **cfd}


def _cost_dict(name: str, code: str, is_cfd: bool, price: float, spreads: dict,
               specs_fx: dict, specs_cfd: dict, swap_mult: float = 1.0) -> dict:
    sm = spreads[code]
    spread_frac = (sm["overall"]["p50"] or 0.0) * sm["pip"] / price   # cruzar o spread 1×
    if is_cfd:
        s = specs_cfd[name]
        contract, tick_val = s["contract_size"], s["tick_value"]
        swap_l, swap_s = s["swap_long"], s["swap_short"]
        comm = 0.0                                    # comissão de CFD ainda não medida (otimista)
    else:
        s = specs_fx[name]
        contract, tick_val = s["contract_size"], s["tick_value"]
        swap_l, swap_s = s["swap_long"], s["swap_short"]
        comm = GOLD_COMM_RT if name == "XAUUSD" else FX_COMM_RT
    notional = contract if _base_is_usd(name) else contract * price   # por lote
    return {"spread_frac": spread_frac, "comm_frac": comm,
            "swap_long_frac": swap_l * tick_val / notional * swap_mult,
            "swap_short_frac": swap_s * tick_val / notional * swap_mult}


def _d1_by_inst() -> dict:
    out = {}
    for name, (code, _) in UNIV.items():
        h1 = pd.read_parquet(Path("data/bars") / code / "1h.parquet")
        out[name] = resample_d1(h1)
    return out


def evaluate(net: np.ndarray, gross: np.ndarray) -> dict:
    idx = pd.RangeIndex(len(net))
    sr_net, sr_gross = _sharpe(net), _sharpe(gross)
    psr = probabilistic_sharpe_ratio(net) if net.std() > 0 else 0.0
    # blocos temporais (doc: positivo em >=3/5)
    blocks = np.array_split(net, 5)
    blk_sr = [_sharpe(b) for b in blocks]
    blk_pos = int(sum(s > 0 for s in blk_sr))
    # CPCV
    days = pd.date_range("2010-01-01", periods=len(net), freq="B")
    t1 = make_label_spans(days, horizon=1)
    oos = np.array([_sharpe(net[te]) for _, te in
                    CombinatorialPurgedCV(n_groups=8, n_test_groups=2).split(t1)])
    n_trials = max(AttemptRegistry("experiments/attempts.db").count(), 1)
    dsr = deflated_sharpe_ratio(net, sr_variance=max(float((oos / ANN).var(ddof=1)), 1e-9),
                                n_trials=n_trials)
    mc = mc_distribution(net[net != 0], block_size=20, n_sims=2000, rng=np.random.default_rng(42))
    return {"sharpe_net": round(sr_net, 3), "sharpe_gross": round(sr_gross, 3),
            "net_over_gross": round(sr_net / sr_gross, 2) if sr_gross > 0 else None,
            "psr": round(psr, 4), "blocks_sharpe": [round(x, 2) for x in blk_sr],
            "blocks_positive": blk_pos, "cpcv_pct_positive": round(float((oos > 0).mean()), 3),
            "dsr": round(dsr, 4), "mc_maxdd_p99": round(mc["max_drawdown"]["p99"], 5)}


def run(swap_mult: float = 1.0) -> dict:
    spreads = _spread_models()
    specs_fx = json.loads(Path("experiments/broker_specs.json").read_text())["symbols"]
    specs_cfd = json.loads(Path("experiments/broker_specs_intraday.json").read_text())["symbols"]
    d1 = _d1_by_inst()
    pnls, per_inst = {}, {}
    for name, (code, is_cfd) in UNIV.items():
        price = float(d1[name]["close"].median())
        cost = _cost_dict(name, code, is_cfd, price, spreads, specs_fx, specs_cfd, swap_mult)
        p = instrument_pnl(d1[name], cost)
        pnls[name] = p
        per_inst[name] = {"gross": round(float(p["gross"].sum()), 4),
                          "swap": round(float(p["swap"].sum()), 4),
                          "net": round(float(p["net"].sum()), 4)}
    port = portfolio(pnls)
    ev = evaluate(port["net"].to_numpy(), port["gross"].to_numpy())
    doc_gate = bool(ev["sharpe_net"] > 0.3 and ev["blocks_positive"] >= 3
                    and (ev["net_over_gross"] or 0) >= 0.60)
    strict_gate = bool(ev["sharpe_net"] > 0 and ev["psr"] > 0.95
                       and ev["cpcv_pct_positive"] >= 0.60 and ev["dsr"] > 0)
    return {"phase": "1d", "strategy": "TSMOM D1 cross-asset (Part 13)", "swap_mult": swap_mult,
            **ev, "doc_phase1_gate": doc_gate, "strict_gate": strict_gate,
            "verdict": "PASS" if doc_gate else "FAIL", "per_instrument": per_inst}


def main() -> None:
    base = run(swap_mult=1.0)
    stress = run(swap_mult=2.0)  # doc: sobrevive a swap ×2?
    base["stress_swap2x_sharpe_net"] = stress["sharpe_net"]
    base["survives_swap2x"] = bool(stress["sharpe_net"] > 0)
    Path("experiments/tsmom_1d.json").write_text(json.dumps(base, indent=2, ensure_ascii=False),
                                                 encoding="utf-8")
    print(json.dumps({k: v for k, v in base.items() if k != "per_instrument"},
                     indent=2, ensure_ascii=False))
    print("por ativo (gross | swap | net):")
    for k, v in base["per_instrument"].items():
        print(f"  {k:7} {v['gross']:>9} | {v['swap']:>9} | {v['net']:>9}")
    print("WROTE experiments/tsmom_1d.json")


if __name__ == "__main__":
    main()
