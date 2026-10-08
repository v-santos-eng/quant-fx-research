"""Piloto do baseline ORB (Fase 1i) — GER40. Spread par×hora medido (p75), comissão
parametrizada (0 = spread-only, caso OTIMISTA). Reporta net/gross/custo, Sharpe diário
anualizado e PSR, e o 1º corte do gate: **bruto positivo**. Não é o gate completo
(CPCV/DSR/MC vêm depois se o bruto passar) — é o corte que matou o FX na Fase 1.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from research.costs import SymbolCost
from research.orb import ORBParams, orb_trades
from research.validation import probabilistic_sharpe_ratio, sharpe_ratio

CAPITAL = 1000.0
SPREAD_MODEL = Path("experiments/spread_model_intraday.json")


def _spread_by_hour(datafeed_code: str, pct: str = "p75") -> dict[int, float]:
    models = json.loads(SPREAD_MODEL.read_text(encoding="utf-8"))
    m = next(x for x in models if x["symbol"] == datafeed_code)
    out = {int(h): (v[pct] or 0.0) for h, v in m["by_hour_utc"].items()}
    out[-1] = m["overall"][pct] or 0.0  # fallback
    return out


def run(name: str, commission_per_million: float = 0.0, pct: str = "p75") -> dict:
    cfg = yaml.safe_load(Path("config/instruments_intraday.yaml").read_text("utf-8"))["instruments"]
    c = cfg[name]
    bars = pd.read_parquet(Path("data/bars") / c["datafeed_code"] / "15min.parquet")
    sc = SymbolCost(name, pip=c["pip"], point=c["point"], contract=c["contract_size"],
                    commission_per_million_usd=commission_per_million,
                    swap_long_points=0.0, swap_short_points=0.0)
    res = orb_trades(bars, c["session_utc"], sc, _spread_by_hour(c["datafeed_code"], pct),
                     params=ORBParams(), lots=c["volume_min"])
    trades = res["trades"]
    s = res["summary"]

    # série de P&L diária sobre TODOS os dias de sessão (0 nos dias sem trade) -> Sharpe honesto
    days = pd.to_datetime(bars["timestamp"]).dt.date
    all_days = pd.Index(sorted(set(days)))
    pnl = pd.Series(0.0, index=all_days)
    for t in trades:
        d = pd.Timestamp(t["entry_time"]).date()
        pnl[d] += t["net_usd"]
    ret = (pnl / CAPITAL).to_numpy()
    sr_ann = sharpe_ratio(ret, periods_per_year=252) if ret.std() > 0 else 0.0
    psr = probabilistic_sharpe_ratio(ret) if ret.std() > 0 else 0.0
    years = max((all_days[-1] - all_days[0]).days / 365.25, 1e-9)

    out = {
        "instrument": name, "commission_per_million": commission_per_million, "spread_pct": pct,
        "n_trades": s["n_trades"], "trades_per_year": round(s["n_trades"] / years, 1),
        "gross_usd": s["gross_usd"], "cost_usd": s["cost_usd"], "net_usd": s["net_usd"],
        "win_rate": s["win_rate"], "sharpe_ann": round(sr_ann, 3), "psr": round(psr, 4),
        "gross_positive": bool(s["gross_usd"] > 0), "years": round(years, 1),
    }
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--instrument", default="GER40")
    p.add_argument("--commission", type=float, nargs="+", default=[0.0],
                   help="comissão(ões) USD/milhão para sensibilidade")
    a = p.parse_args()
    print(f"=== Piloto ORB — {a.instrument} ===")
    results = [run(a.instrument, comm) for comm in a.commission]
    for o in results:
        print(f"comm={o['commission_per_million']:>5}/M | trades={o['n_trades']} "
              f"({o['trades_per_year']}/ano) | bruto=${o['gross_usd']} custo=${o['cost_usd']} "
              f"net=${o['net_usd']} | win={o['win_rate']} | Sharpe={o['sharpe_ann']} "
              f"PSR={o['psr']} | bruto+={o['gross_positive']}")
    Path("experiments").mkdir(exist_ok=True)
    Path("experiments/orb_pilot.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("WROTE experiments/orb_pilot.json")


if __name__ == "__main__":
    main()
