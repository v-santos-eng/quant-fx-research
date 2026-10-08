"""Baseline ORB intraday (Fase 1i) + dataset para meta-labeling (Fase 2i).

Opening-Range Breakout + filtro de VWAP de sessão, saída por BRACKET (stop no lado oposto
do OR ou ATR — o mais apertado; alvo R_MULT×risco; flat forçado no fim da sessão).
Determinístico e SEM look-ahead: gatilho decidido no FECHAMENTO da barra M15, entrada na
ABERTURA seguinte; stop/alvo checados INTRABAR por high/low. Custo: spread par×hora + comissão;
**swap = 0**. Uma entrada por instrumento por sessão. Spec: docs/baseline_orb.md.

`_iter_signals` é a FONTE ÚNICA da lógica de bracket: `orb_trades` (backtest) e `orb_dataset`
(features + rótulo p/ o ML) consomem o mesmo gerador — não podem divergir.

ponytail: P&L em pontos do índice × valor-do-ponto (USD via SymbolCost). Conversão EUR→USD
histórica do GER40 é refino da Fase 2 — não muda o SINAL do edge bruto (1º corte).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from research.backtester import Trade
from research.costs import SymbolCost, pip_value_usd, round_trip_cost_usd
from research.indicators import wilder_atr


@dataclass(frozen=True)
class ORBParams:
    or_min: int = 30
    tf_min: int = 15
    atr_mult: float = 1.0
    r_mult: float = 2.0
    k_range: float = 0.5
    atr_n: int = 14


def _session_mask(ts: pd.Series, session_utc: str) -> np.ndarray:
    a, b = session_utc.split("-")
    sh, sm = (int(x) for x in a.split(":"))
    eh, em = (int(x) for x in b.split(":"))
    minute = ts.dt.hour * 60 + ts.dt.minute
    start, end = sh * 60 + sm, eh * 60 + em
    if start <= end:
        return ((minute >= start) & (minute < end)).to_numpy()
    return ((minute >= start) | (minute < end)).to_numpy()


def _iter_signals(bars: pd.DataFrame, session_utc: str, params: ORBParams):
    """Gera um sinal ORB por sessão (quando há): entry/stop/alvo, desfecho intrabar e FEATURES.

    Yield: dict com trade (dirn, entry_time, entry, exit_time, exit_price) + 'feat' (dict de features
    calculadas SÓ com info até a barra-gatilho — sem look-ahead).
    """
    b = bars.loc[_session_mask(bars["timestamp"], session_utc)].reset_index(drop=True)
    if b.empty:
        return
    ts = pd.to_datetime(b["timestamp"])
    o, h, l, c = (b[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    vol = b["volume"].to_numpy(float)
    atr = wilder_atr(h, l, c, params.atr_n)
    atr_med = pd.Series(atr).rolling(500, min_periods=50).median().to_numpy()  # regime de vol
    n_or = max(1, math.ceil(params.or_min / params.tf_min))
    minute = (ts.dt.hour * 60 + ts.dt.minute).to_numpy()
    dow = ts.dt.weekday.to_numpy()
    day = ts.dt.date.to_numpy()
    starts = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    bounds = list(starts) + [len(b)]
    sess_start = minute[starts[0]] if len(starts) else 0

    # retorno do dia anterior (close_fim - open_ini)/open_ini, indexado por posição de dia
    day_ret = {}
    for di, (s, e) in enumerate(zip(bounds[:-1], bounds[1:])):
        day_ret[di] = (c[e - 1] - o[s]) / o[s] if o[s] else 0.0

    for di, (s, e) in enumerate(zip(bounds[:-1], bounds[1:])):
        if e - s <= n_or:
            continue
        or_hi, or_lo = h[s:s + n_or].max(), l[s:s + n_or].min()
        or_w = or_hi - or_lo
        a_or = atr[s + n_or - 1]
        if not np.isfinite(a_or) or or_w < params.k_range * a_or:
            continue
        typ = (h[s:e] + l[s:e] + c[s:e]) / 3.0
        cum_pv, cum_v = np.cumsum(typ * vol[s:e]), np.cumsum(vol[s:e])
        vwap = np.divide(cum_pv, cum_v, out=np.full_like(cum_pv, np.nan), where=cum_v > 0)
        trig = None
        for j in range(s + n_or, e):
            k = j - s
            if c[j] > or_hi and c[j] > vwap[k]:
                trig = (j, +1); break
            if c[j] < or_lo and c[j] < vwap[k]:
                trig = (j, -1); break
        if trig is None:
            continue
        j, dirn = trig
        if j + 1 >= e:
            continue
        entry = o[j + 1]
        a_e = atr[j]
        stop_dist = (min(entry - or_lo, params.atr_mult * a_e) if dirn > 0
                     else min(or_hi - entry, params.atr_mult * a_e))
        if not np.isfinite(stop_dist) or stop_dist <= 0:
            continue
        stop = entry - dirn * stop_dist
        target = entry + dirn * params.r_mult * stop_dist
        exit_price, exit_i = c[e - 1], e - 1
        for m in range(j + 1, e):
            if dirn > 0:
                if l[m] <= stop:  exit_price, exit_i = stop, m; break
                if h[m] >= target: exit_price, exit_i = target, m; break
            else:
                if h[m] >= stop:  exit_price, exit_i = stop, m; break
                if l[m] <= target: exit_price, exit_i = target, m; break
            if m == e - 1:
                exit_price, exit_i = c[m], m
        # --- features (só info até a barra-gatilho j) ---
        kk = j - s
        med = atr_med[j]
        feat = {
            "or_width_atr": float(or_w / a_or) if a_or > 0 else 0.0,
            "dist_vwap_atr": float((c[j] - vwap[kk]) * dirn / a_e) if a_e > 0 else 0.0,
            "atr_regime": float(a_e / med) if np.isfinite(med) and med > 0 else 1.0,
            "minute_of_session": float(minute[j] - sess_start),
            "prev_day_ret": float(day_ret.get(di - 1, 0.0)),
            "h1_slope_atr": float((c[j] - c[j - 4]) * dirn / a_e) if j - 4 >= s and a_e > 0 else 0.0,
            "or_vol_ratio": float(vol[s:s + n_or].mean() / max(vol[s:j + 1].mean(), 1e-9)),
            "dow": float(dow[j]),
            "direction": int(dirn),
        }
        yield {"dirn": dirn, "entry_time": ts.iloc[j + 1], "entry": float(entry),
               "exit_time": ts.iloc[exit_i], "exit_price": float(exit_price), "feat": feat}


def _mk_trade(sc, dirn, t_in, entry, t_out, exit_price, lots, spread_by_hour, slip) -> Trade:
    direction = "long" if dirn > 0 else "short"
    gross = (exit_price - entry) * dirn / sc.pip * pip_value_usd(sc, exit_price) * lots
    spread = spread_by_hour.get(pd.Timestamp(t_in).hour, spread_by_hour.get(-1, 0.0))
    cost = round_trip_cost_usd(sc, spread, entry, lots, direction, nights=0,
                               slippage_mult=slip)["total_cost"]
    return Trade(sc.symbol, direction, str(t_in), float(entry), str(t_out), float(exit_price),
                 lots, 0, round(gross, 2), round(cost, 2), round(gross - cost, 2))


def orb_trades(bars, session_utc, sc: SymbolCost, spread_by_hour, params: ORBParams = ORBParams(),
               lots: float = 0.1, slippage_mult: float = 0.0) -> dict:
    """Backtest do baseline ORB sobre barras M15 de UM instrumento. Retorna trades + resumo."""
    trades = [_mk_trade(sc, g["dirn"], g["entry_time"], g["entry"], g["exit_time"],
                        g["exit_price"], lots, spread_by_hour, slippage_mult)
              for g in _iter_signals(bars, session_utc, params)]
    return {"trades": [asdict(t) for t in trades], "summary": _summary(sc.symbol, trades)}


def orb_dataset(bars, session_utc, sc: SymbolCost, spread_by_hour,
                params: ORBParams = ORBParams(), lots: float = 0.1, slippage_mult: float = 0.0):
    """DataFrame com uma linha por sinal ORB: features + net_usd + y (1 = trade líquido vencedor).
    Base do meta-labeling (Fase 2i). Ordenado por entry_time."""
    rows = []
    for g in _iter_signals(bars, session_utc, params):
        t = _mk_trade(sc, g["dirn"], g["entry_time"], g["entry"], g["exit_time"],
                      g["exit_price"], lots, spread_by_hour, slippage_mult)
        rows.append({"entry_time": g["entry_time"], "exit_time": pd.Timestamp(t.exit_time),
                     "net_usd": t.net_usd, "gross_usd": t.gross_usd, "cost_usd": t.cost_usd,
                     "y": int(t.net_usd > 0), **g["feat"]})
    return pd.DataFrame(rows)


def _summary(symbol: str, trades: list[Trade]) -> dict:
    wins = [t for t in trades if t.net_usd > 0]
    return {"symbol": symbol, "n_trades": len(trades),
            "net_usd": round(sum(t.net_usd for t in trades), 2),
            "gross_usd": round(sum(t.gross_usd for t in trades), 2),
            "cost_usd": round(sum(t.cost_usd for t in trades), 2),
            "win_rate": round(len(wins) / len(trades), 3) if trades else None}
