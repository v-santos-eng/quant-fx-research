"""Construção de barras OHLC a partir de ticks (Fase 0.4). A régua temporal do sistema.

Barras no preço médio (mid) por padrão — convenção para sinais; execução usa bid/ask.
Alinhamento por padrão a meia-noite UTC (H4 -> 00,04,08,12,16,20 UTC).

ATENÇÃO reconciliação (R-01): o MT5 alinha barras ao horário do SERVIDOR (Dukascopy
não é UTC), então para bater com o Strategy Tester é preciso passar `origin_offset`
igual ao offset do servidor. Documentado aqui porque é fonte clássica de divergência.
"""
from __future__ import annotations

import pandas as pd

from research.sanity import _check_columns

_PRICE = {"mid": lambda d: (d["bid"] + d["ask"]) / 2,
          "bid": lambda d: d["bid"],
          "ask": lambda d: d["ask"]}


def build_bars(ticks: pd.DataFrame, freq: str, price: str = "mid",
               origin_offset: pd.Timedelta | None = None) -> pd.DataFrame:
    """Ticks -> OHLC no `freq` dado (ex.: '1h', '4h').

    price: 'mid'|'bid'|'ask'. origin_offset desloca o alinhamento das barras (para
    casar com o horário do servidor MT5 na reconciliação). Barras vazias (fim de
    semana) são removidas. Barra rotulada no seu início; intervalo [início, início+freq).
    """
    _check_columns(ticks)
    if price not in _PRICE:
        raise ValueError(f"price deve ser mid|bid|ask, veio {price!r}")
    if ticks.empty:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    p = _PRICE[price](ticks)
    ts = pd.to_datetime(ticks["timestamp"])
    if origin_offset is not None:
        ts = ts - origin_offset
    s = pd.Series(p.to_numpy(), index=pd.DatetimeIndex(ts)).sort_index()

    bars = s.resample(freq, label="left", closed="left").ohlc()
    bars["volume"] = s.resample(freq, label="left", closed="left").count()
    bars = bars.dropna(subset=["open"])
    bars.index = bars.index + origin_offset if origin_offset is not None else bars.index
    return bars.reset_index(names="timestamp")
