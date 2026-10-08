"""Baseline TSMOM D1 cross-asset (Part 13 / Phase 1 do design doc). PURO/testável.

Sinal: time-series momentum multi-horizonte — sinal do retorno passado em 3 lookbacks
(~21/63/126d), média = score por ativo (Moskowitz-Ooi-Pedersen 2012). Posição ∝ score,
escalada por inverse-vol (cada ativo mira risco similar). Rebalance só quando o alvo desvia
> band do mantido (controla turnover). Holding overnight → paga SWAP (custo central do doc).

Sem look-ahead: decisão no fechamento de t (dados até t), P&L no retorno de t+1.
Avaliação em espaço de RETORNO (Sharpe é invariante à escala; vol-targeting não muda Sharpe).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.backtester import _swap_nights


def resample_d1(h1: pd.DataFrame) -> pd.DataFrame:
    s = h1.set_index("timestamp").sort_index()
    d = s.resample("1D").agg(open=("open", "first"), high=("high", "max"),
                             low=("low", "min"), close=("close", "last"),
                             volume=("volume", "sum")).dropna(subset=["close"])
    return d


def tsmom_score(close: pd.Series, lookbacks=(21, 63, 126)) -> pd.Series:
    """Média do SINAL do retorno passado em cada lookback -> score em [-1, 1]. NaN no warmup."""
    return sum(np.sign(close / close.shift(L) - 1.0) for L in lookbacks) / len(lookbacks)


def ewma_vol(ret: pd.Series, halflife: int = 32) -> pd.Series:
    return ret.ewm(halflife=halflife, min_periods=20).std()


def _held_with_band(target: pd.Series, band: float) -> pd.Series:
    """Aplica banda de drift: só muda o peso mantido quando o alvo desvia > band*|mantido|
    (ou cruza zero / sai do flat). Reduz turnover — fiel ao doc ('rebalance quando drift > 20%')."""
    t = target.to_numpy()
    held = np.zeros(len(t))
    cur = 0.0
    for i in range(len(t)):
        tg = t[i]
        if not np.isfinite(tg):
            held[i] = cur; continue
        if cur == 0.0 or tg == 0.0 or np.sign(tg) != np.sign(cur) \
                or abs(tg - cur) > band * abs(cur):
            cur = tg
        held[i] = cur
    return pd.Series(held, index=target.index)


def instrument_pnl(d1: pd.DataFrame, cost: dict, lookbacks=(21, 63, 126), vol_hl: int = 32,
                   target_dv: float = 0.004, band: float = 0.20) -> pd.DataFrame:
    """Série diária de P&L (fração de notional) de UM ativo: gross, custos e net.

    cost: {spread_frac, comm_frac, swap_long_frac, swap_short_frac} (frações por notional;
    swap_*_frac = P&L por noite, sinal negativo = débito).
    """
    close = d1["close"]
    ret = close.pct_change()
    score = tsmom_score(close, lookbacks)
    vol = ewma_vol(ret, vol_hl)
    target = (score * (target_dv / vol)).clip(-4.0, 4.0)     # inverse-vol, cap sanity
    held = _held_with_band(target.fillna(0.0), band)
    w_prev = held.shift(1).fillna(0.0)                        # peso que rende o retorno de hoje

    gross = w_prev * ret
    turn = (held - held.shift(1)).abs().fillna(held.abs())
    spread_c = turn * cost["spread_frac"]
    comm_c = turn * cost["comm_frac"]
    # swap: noites de rollover por passo (quarta ×3, fim de semana), direção do peso mantido
    idx = d1.index
    nights = np.zeros(len(idx))
    for i in range(1, len(idx)):
        nights[i] = _swap_nights(idx[i - 1], idx[i])
    swap_frac = np.where(w_prev.to_numpy() >= 0, cost["swap_long_frac"], cost["swap_short_frac"])
    swap_pnl = pd.Series(w_prev.abs().to_numpy() * swap_frac * nights, index=idx)

    net = gross - spread_c - comm_c + swap_pnl
    return pd.DataFrame({"gross": gross, "spread": spread_c, "comm": comm_c,
                         "swap": swap_pnl, "net": net})


def tsmom_score_prop(close: pd.Series, vol_daily: pd.Series, lookbacks=(21, 63, 126),
                     cap: float = 2.0) -> pd.Series:
    """Score PROPORCIONAL (Part 13): média do retorno vol-normalizado (z ~ t-stat de momentum)
    em cada lookback, saturado em ±cap. Substitui o sinal binário — dá mais peso a tendências
    fortes e quase-zero a instrumentos sem trend (derruba os majors por conta própria)."""
    z = sum((close / close.shift(L) - 1.0) / (vol_daily * np.sqrt(L)) for L in lookbacks) / len(lookbacks)
    return z.clip(-cap, cap)


def instrument_weight(d1: pd.DataFrame, lookbacks=(21, 63, 126), vol_hl: int = 32,
                      target_dv: float = 0.004, band: float = 0.20,
                      proportional: bool = True, cap: float = 2.0):
    """Peso-alvo mantido (com banda de drift) + retorno diário, para UM ativo."""
    close = d1["close"]
    ret = close.pct_change()
    vol = ewma_vol(ret, vol_hl)
    score = (tsmom_score_prop(close, vol, lookbacks, cap) if proportional
             else tsmom_score(close, lookbacks))
    target = (score * (target_dv / vol)).clip(-4.0, 4.0)
    held = _held_with_band(target.fillna(0.0), band)
    return held, ret


def apply_costs(held: pd.Series, ret: pd.Series, index, cost: dict,
                exposure: pd.Series | None = None) -> pd.DataFrame:
    """P&L diário (fração de notional) dado o peso mantido, custos e um multiplicador de
    exposição opcional (overlay de regime). final = held × exposure."""
    w = held if exposure is None else (held * exposure.reindex(held.index).fillna(1.0))
    w_prev = w.shift(1).fillna(0.0)
    gross = w_prev * ret
    turn = (w - w.shift(1)).abs().fillna(w.abs())
    spread_c = turn * cost["spread_frac"]
    comm_c = turn * cost["comm_frac"]
    nights = np.zeros(len(index))
    for i in range(1, len(index)):
        nights[i] = _swap_nights(index[i - 1], index[i])
    swap_frac = np.where(w_prev.to_numpy() >= 0, cost["swap_long_frac"], cost["swap_short_frac"])
    swap_pnl = pd.Series(w_prev.abs().to_numpy() * swap_frac * nights, index=index)
    net = gross - spread_c - comm_c + swap_pnl
    return pd.DataFrame({"gross": gross, "spread": spread_c, "comm": comm_c,
                         "swap": swap_pnl, "net": net})


def regime_overlay(base_gross: pd.Series, vol_win: int = 63, pct_win: int = 504,
                   pct: float = 0.90, scale_down: float = 0.5) -> pd.Series:
    """Multiplicador de exposição: reduz p/ scale_down quando a vol realizada do portfólio passa
    do percentil `pct` da própria história recente (Part 9). Sem look-ahead: decisão em t-1."""
    rv = base_gross.rolling(vol_win, min_periods=vol_win // 2).std()
    thr = rv.rolling(pct_win, min_periods=pct_win // 2).quantile(pct)
    ov = pd.Series(np.where(rv > thr, scale_down, 1.0), index=base_gross.index)
    return ov.shift(1).fillna(1.0)


def portfolio(pnls: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Soma as séries por ativo num calendário comum (ativo ausente no dia = 0)."""
    allidx = sorted(set().union(*[p.index for p in pnls.values()]))
    idx = pd.DatetimeIndex(allidx)
    out = pd.DataFrame(0.0, index=idx, columns=["gross", "spread", "comm", "swap", "net"])
    for p in pnls.values():
        out = out.add(p.reindex(idx).fillna(0.0), fill_value=0.0)
    return out
