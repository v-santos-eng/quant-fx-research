"""Fase 1d — TSMOM D1 COMPLETO da Part 13: score proporcional (z-score) + overlay de regime
(reduz exposição quando a vol do portfólio passa do p90). Testa se o sizing proporcional derruba
os majors sem-trend SEM seleção ex-post. Mesmo gate e custos medidos de run_tsmom.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.run_tsmom import (UNIV, _cost_dict, _d1_by_inst, _spread_models, evaluate)
from research.tsmom import apply_costs, instrument_weight, portfolio, regime_overlay

BOOKS = {
    "FX+ouro (6, a-priori)": ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "XAUUSD"],
    "8 ativos (doc)": list(UNIV),
    "USDJPY+XAUUSD": ["USDJPY", "XAUUSD"],
}


def run_book(names, d1, spreads, sfx, scfd, regime=True) -> dict:
    weights, rets, costs = {}, {}, {}
    for name in names:
        code, is_cfd = UNIV[name]
        price = float(d1[name]["close"].median())
        w, r = instrument_weight(d1[name], proportional=True)
        weights[name], rets[name] = w, r
        costs[name] = _cost_dict(name, code, is_cfd, price, spreads, sfx, scfd, 1.0)
    idx = pd.DatetimeIndex(sorted(set().union(*[w.index for w in weights.values()])))
    # portfolio gross base (para detectar regime) — sem custo, sem overlay
    base = pd.Series(0.0, index=idx)
    for name in names:
        w_prev = weights[name].shift(1).reindex(idx).fillna(0.0)
        base = base.add(w_prev * rets[name].reindex(idx).fillna(0.0), fill_value=0.0)
    overlay = regime_overlay(base) if regime else None
    pnls = {name: apply_costs(weights[name], rets[name], d1[name].index, costs[name], overlay)
            for name in names}
    port = portfolio(pnls)
    ev = evaluate(port["net"].to_numpy(), port["gross"].to_numpy())
    return ev


def main() -> None:
    spreads = _spread_models()
    sfx = json.loads(Path("experiments/broker_specs.json").read_text())["symbols"]
    scfd = json.loads(Path("experiments/broker_specs_intraday.json").read_text())["symbols"]
    d1 = _d1_by_inst()
    out = {}
    for label, names in BOOKS.items():
        ev = run_book(names, d1, spreads, sfx, scfd, regime=True)
        gate = bool(ev["sharpe_net"] > 0.3 and ev["blocks_positive"] >= 3
                    and ev["psr"] > 0.95 and ev["cpcv_pct_positive"] >= 0.60 and ev["dsr"] > 0)
        ev["gate_pass"] = gate
        out[label] = ev
        print(f"{label:24} SharpeNet={ev['sharpe_net']:+.3f} gross={ev['sharpe_gross']:+.3f} "
              f"PSR={ev['psr']} blocos+={ev['blocks_positive']}/5 CPCV+={ev['cpcv_pct_positive']} "
              f"DSR={ev['dsr']} net/gross={ev['net_over_gross']} -> {'PASS' if gate else 'FAIL'}")
    Path("experiments/tsmom_full_1d.json").write_text(json.dumps(out, indent=2, ensure_ascii=False),
                                                      encoding="utf-8")
    print("WROTE experiments/tsmom_full_1d.json")


if __name__ == "__main__":
    main()
