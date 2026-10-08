"""Baseline de REVERSÃO intraday (Fase 2a) — hipótese alternativa ao ORB.

Racional (a priori): a extensão excessiva da sessão para longe do VWAP se corrige — excesso
de fluxo/liquidez na abertura reverte à média. Mecanismo DIFERENTE do ORB (continuação), não
uma variação dele. FADE quando o preço se estica ≥ Z·ATR do VWAP; ALVO = volta ao VWAP
(dinâmico); STOP se a extensão continua (S·ATR além da entrada); flat no fim da sessão (swap=0).

Determinístico, sem look-ahead: gatilho no FECHAMENTO da barra, entrada na ABERTURA seguinte,
alvo/stop checados INTRABAR. Reusa a infra do ORB (slicing de sessão, custo, ATR).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from research.indicators import wilder_atr
from research.orb import _mk_trade, _session_mask, _summary


@dataclass(frozen=True)
class MRParams:
    z: float = 1.5          # limiar de extensão (em ATR) do VWAP para fazer o fade
    stop_atr: float = 1.0   # stop = S·ATR além da entrada (extensão continua)
    warmup_min: int = 30    # ignora o início da sessão (VWAP/ATR instáveis)
    tf_min: int = 15
    atr_n: int = 14


def _iter_signals(bars: pd.DataFrame, session_utc: str, params: MRParams):
    b = bars.loc[_session_mask(bars["timestamp"], session_utc)].reset_index(drop=True)
    if b.empty:
        return
    ts = pd.to_datetime(b["timestamp"])
    o, h, l, c = (b[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    vol = b["volume"].to_numpy(float)
    atr = wilder_atr(h, l, c, params.atr_n)
    warmup = max(1, math.ceil(params.warmup_min / params.tf_min))
    day = ts.dt.date.to_numpy()
    starts = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    bounds = list(starts) + [len(b)]

    for s, e in zip(bounds[:-1], bounds[1:]):
        if e - s <= warmup:
            continue
        typ = (h[s:e] + l[s:e] + c[s:e]) / 3.0
        cum_pv, cum_v = np.cumsum(typ * vol[s:e]), np.cumsum(vol[s:e])
        vwap = np.divide(cum_pv, cum_v, out=np.full_like(cum_pv, np.nan), where=cum_v > 0)
        trig = None
        for j in range(s + warmup, e):
            k = j - s
            a = atr[j]
            if not np.isfinite(a) or a <= 0 or not np.isfinite(vwap[k]):
                continue
            dev = c[j] - vwap[k]
            if dev >= params.z * a:
                trig = (j, -1); break      # esticou p/ CIMA -> fade SHORT
            if dev <= -params.z * a:
                trig = (j, +1); break      # esticou p/ BAIXO -> fade LONG
        if trig is None:
            continue
        j, dirn = trig
        if j + 1 >= e:
            continue
        entry = o[j + 1]
        stop_dist = params.stop_atr * atr[j]
        if stop_dist <= 0:
            continue
        stop = entry - dirn * stop_dist        # long: abaixo; short: acima
        exit_price, exit_i = c[e - 1], e - 1
        for m in range(j + 1, e):
            k = m - s
            tgt = vwap[k]                       # alvo dinâmico = VWAP corrente
            if dirn > 0:  # fade long (entrou abaixo do VWAP): sai ao subir p/ o VWAP; stop abaixo
                if l[m] <= stop:  exit_price, exit_i = stop, m; break
                if h[m] >= tgt:   exit_price, exit_i = tgt, m; break
            else:         # fade short (entrou acima): sai ao cair p/ o VWAP; stop acima
                if h[m] >= stop:  exit_price, exit_i = stop, m; break
                if l[m] <= tgt:   exit_price, exit_i = tgt, m; break
            if m == e - 1:
                exit_price, exit_i = c[m], m
        yield {"dirn": dirn, "entry_time": ts.iloc[j + 1], "entry": float(entry),
               "exit_time": ts.iloc[exit_i], "exit_price": float(exit_price)}


def mr_trades(bars, session_utc, sc, spread_by_hour, params: MRParams = MRParams(),
              lots: float = 0.1, slippage_mult: float = 0.0) -> dict:
    """Backtest do baseline de reversão. Mesma forma de retorno do orb_trades."""
    trades = [_mk_trade(sc, g["dirn"], g["entry_time"], g["entry"], g["exit_time"],
                        g["exit_price"], lots, spread_by_hour, slippage_mult)
              for g in _iter_signals(bars, session_utc, params)]
    return {"trades": [asdict(t) for t in trades], "summary": _summary(sc.symbol, trades)}
