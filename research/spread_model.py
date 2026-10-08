"""Modelo de spread por par x hora-do-dia UTC, do bid/ask histórico da Dukascopy.

Como o broker agora é Dukascopy (mesmo venue), o spread histórico é representativo
do raw ECN que se paga (a comissão entra à parte). Streaming por arquivo; acumula
um histograma de spread (em pips) por (par, hora) — memória O(pares×24×bins), e tira
percentis p50/p75/p90 do histograma cumulativo. O p75 alimenta o filtro (RF-09).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from research.attempt_registry import AttemptRegistry

DATA_ROOT = Path("data/dukascopy")
OUT = Path("experiments/spread_model.json")
NBINS = 1000
# teto de spread em pips por par para o grid do histograma (spreads acima caem no topo)
MAXPIP = {"EURUSD": 5.0, "GBPUSD": 6.0, "AUDUSD": 6.0, "USDCAD": 8.0,
          "USDJPY": 5.0, "XAUUSD": 60.0}


def _pips(symbols_cfg: dict) -> dict:
    return {s: symbols_cfg[s]["pip"] for s in symbols_cfg}


def _percentiles_from_hist(counts: np.ndarray, maxpip: float, ps=(0.5, 0.75, 0.9)) -> dict:
    total = counts.sum()
    if total == 0:
        return {f"p{int(p*100)}": None for p in ps}
    edges = np.linspace(0, maxpip, NBINS + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    cum = np.cumsum(counts)
    out = {}
    for p in ps:
        i = int(np.searchsorted(cum, p * total))
        out[f"p{int(p * 100)}"] = round(float(centers[min(i, NBINS - 1)]), 4)
    return out


def model_symbol(symbol: str, pip: float, maxpip: float | None = None) -> dict:
    files = sorted((DATA_ROOT / symbol).rglob("*.parquet"))
    maxpip = MAXPIP[symbol] if maxpip is None else maxpip
    hist = np.zeros((24, NBINS), dtype=np.int64)
    n_ticks = 0
    for i, f in enumerate(files):
        df = pd.read_parquet(f)
        if not len(df):
            continue
        sp = (df["ask"].to_numpy() - df["bid"].to_numpy()) / pip
        sp = np.clip(sp, 0, maxpip)
        idx = np.minimum((sp / maxpip * NBINS).astype(np.int64), NBINS - 1)
        hours = df["timestamp"].dt.hour.to_numpy()
        for h in range(24):
            m = hours == h
            if m.any():
                hist[h] += np.bincount(idx[m], minlength=NBINS)
        n_ticks += len(df)
        if (i + 1) % 2000 == 0:
            print(f"  {symbol}: {i + 1}/{len(files)}", flush=True)
    by_hour = {h: {"n": int(hist[h].sum()), **_percentiles_from_hist(hist[h], maxpip)}
               for h in range(24)}
    overall = _percentiles_from_hist(hist.sum(axis=0), maxpip)
    return {"symbol": symbol, "pip": pip, "n_ticks": n_ticks,
            "overall": overall, "by_hour_utc": by_hour}


# teto de spread (em pips) por classe de CFD para o grid do histograma.
MAXPIP_CLASS = {"index": 15.0, "metal": 60.0, "commodity": 30.0}


def _intraday_specs() -> tuple[dict, dict]:
    """De config/instruments_intraday.yaml: {datafeed_code: pip} e {code: maxpip}.

    Chaveia pelo CÓDIGO do datafeed (= pasta em data/dukascopy). Pula XAUUSD
    (já modelado no run FX). Teto de spread por classe do instrumento.
    """
    cfg = yaml.safe_load(Path("config/instruments_intraday.yaml").read_text("utf-8"))["instruments"]
    pips, maxpip = {}, {}
    for name, c in cfg.items():
        if name == "XAUUSD":
            continue  # já tem modelo no run FX
        code = c["datafeed_code"]
        pips[code] = c["pip"]
        maxpip[code] = MAXPIP_CLASS[c["class"]]
    return pips, maxpip


def main(pips: dict | None = None, maxpip: dict | None = None,
         out: Path = OUT, phase: str = "0.3") -> None:
    if pips is None:
        symbols_cfg = yaml.safe_load(
            Path("config/symbols.yaml").read_text(encoding="utf-8"))["symbols"]
        pips = _pips(symbols_cfg)
    print(f"=== Modelo de spread (Dukascopy) fase {phase} ===", flush=True)
    models = [model_symbol(s, pips[s], None if maxpip is None else maxpip[s]) for s in pips]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(models, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"WROTE {out}", flush=True)
    for m in models:
        o = m["overall"]
        print(f"{m['symbol']}: spread pips overall p50={o['p50']} p75={o['p75']} p90={o['p90']} "
              f"({m['n_ticks']:,} ticks)", flush=True)
    AttemptRegistry("experiments/attempts.db").log(
        phase=phase, name="spread_model", config_hash="",
        params={"nbins": NBINS, "maxpip": maxpip or MAXPIP},
        result={"overall": {m["symbol"]: m["overall"] for m in models}},
        notes="modelo de spread por instrumento x hora do bid/ask histórico Dukascopy",
    )
    print("LOGGED attempt", flush=True)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--intraday", action="store_true", help="modela os CFDs do universo intraday")
    a = p.parse_args()
    if a.intraday:
        pp, mp = _intraday_specs()
        main(pp, mp, out=Path("experiments/spread_model_intraday.json"), phase="0i")
    else:
        main()
