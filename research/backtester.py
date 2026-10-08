"""Backtester event-driven por barras (Fase 0.4). Estratégia-agnóstico: recebe um
vetor de posição-alvo e simula execução + custos, produzindo blotter e equity.

Convenções (sem look-ahead): a posição é decidida no FECHAMENTO da barra i e
executada na ABERTURA da barra i+1. Custos via research.costs (spread+comissão+swap).
Sizing fixo aqui — gestão de risco é a Fase 2; este engine existe para validar
mecânica e reconciliar com o MT5 (R-01).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from research.costs import SymbolCost, pip_value_usd, round_trip_cost_usd
from research.indicators import adx, wilder_atr


@dataclass(frozen=True)
class Trade:
    symbol: str
    direction: str
    entry_time: str
    entry_price: float
    exit_time: str
    exit_price: float
    lots: float
    nights: int
    gross_usd: float
    cost_usd: float
    net_usd: float


def donchian_positions(bars: pd.DataFrame, entry_n: int = 55, exit_n: int = 20) -> np.ndarray:
    """Posição-alvo por barra: +1/-1/0 (Donchian breakout com saída por canal curto).

    Usa apenas barras passadas [i-n:i] para o canal e o close[i] atual — decidido no
    fechamento de i. Determinístico (base da reconciliação com o EA de referência).
    """
    high, low, close = bars["high"].to_numpy(), bars["low"].to_numpy(), bars["close"].to_numpy()
    n = len(bars)
    pos = np.zeros(n, dtype=np.int8)
    cur = 0
    for i in range(n):
        if i < entry_n:
            continue
        upper, lower = high[i - entry_n:i].max(), low[i - entry_n:i].min()
        ex_up, ex_lo = high[i - exit_n:i].max(), low[i - exit_n:i].min()
        if cur <= 0 and close[i] > upper:
            cur = 1
        elif cur >= 0 and close[i] < lower:
            cur = -1
        elif cur > 0 and close[i] < ex_lo:
            cur = 0
        elif cur < 0 and close[i] > ex_up:
            cur = 0
        pos[i] = cur
    return pos


def canonical_positions(bars: pd.DataFrame, entry_n: int = 55, atr_n: int = 14,
                        atr_mult: float = 3.0, adx_n: int = 14, adx_min: float = 25.0) -> np.ndarray:
    """Baseline CANÔNICO (Parte 13): entrada em rompimento Donchian de `entry_n` barras
    FILTRADA por ADX >= adx_min (só entra em regime de tendência); saída por TRAILING
    STOP de `atr_mult`×ATR; com estado FLAT (não fica sempre no mercado). Determinístico:
    decisão no fechamento, execução na abertura seguinte (via simulate).

    ponytail: stop verificado no CLOSE (não intrabar) -> ligeiramente otimista; upgrade
    para stop intrabar (low/high) se a reconciliação com fills reais pedir.
    """
    high, low, close = (bars[c].to_numpy() for c in ("high", "low", "close"))
    n = len(bars)
    atr = wilder_atr(high, low, close, atr_n)
    adx_v = adx(high, low, close, adx_n)
    pos = np.zeros(n, dtype=np.int8)
    warmup = max(entry_n, 2 * atr_n, 2 * adx_n) + 1
    cur = 0
    stop = extreme = 0.0
    for i in range(n):
        if i < warmup or not np.isfinite(atr[i]):
            continue
        if cur == 0:
            if np.isfinite(adx_v[i]) and adx_v[i] >= adx_min:      # filtro de regime
                upper, lower = high[i - entry_n:i].max(), low[i - entry_n:i].min()
                if close[i] > upper:
                    cur, extreme, stop = 1, close[i], close[i] - atr_mult * atr[i]
                elif close[i] < lower:
                    cur, extreme, stop = -1, close[i], close[i] + atr_mult * atr[i]
        elif cur == 1:
            extreme = max(extreme, close[i])
            stop = max(stop, extreme - atr_mult * atr[i])          # trailing sobe
            if close[i] < stop:
                cur = 0
        else:  # cur == -1
            extreme = min(extreme, close[i])
            stop = min(stop, extreme + atr_mult * atr[i])          # trailing desce
            if close[i] > stop:
                cur = 0
        pos[i] = cur
    return pos


def _swap_nights(t0, t1) -> int:
    """Rollovers de swap entre t0 e t1, modelando o MT5: quarta ×3 (pré-cobra o fim de
    semana), sábado/domingo sem rollover, demais dias ×1. Semana cheia = 7 rollovers.
    """
    d = pd.Timestamp(t0).normalize()
    end = pd.Timestamp(t1).normalize()
    n = 0
    while d < end:
        w = d.weekday()  # 0=seg … 6=dom
        n += 0 if w >= 5 else (3 if w == 2 else 1)
        d += pd.Timedelta(days=1)
    return n


def simulate(bars: pd.DataFrame, target_pos: np.ndarray, sc: SymbolCost,
             spread_pips: float, lots: float = 0.1, slippage_mult: float = 0.0,
             reporter=None) -> dict:
    """Simula execução do vetor de posição sobre as barras. Retorna trades + equity + resumo."""
    ts = bars["timestamp"].to_numpy()
    open_ = bars["open"].to_numpy()
    close = bars["close"].to_numpy()
    n = len(bars)
    trades: list[Trade] = []
    equity = 0.0
    eq_curve = np.zeros(n)
    cur = 0
    entry_price = 0.0
    entry_time = None

    def close_trade(exit_price, exit_time):
        nonlocal equity
        direction = "long" if cur > 0 else "short"
        gross_pips = (exit_price - entry_price) * cur / sc.pip
        gross = gross_pips * pip_value_usd(sc, exit_price) * lots
        nights = _swap_nights(entry_time, exit_time)
        cost = round_trip_cost_usd(sc, spread_pips, entry_price, lots, direction,
                                   nights=nights, slippage_mult=slippage_mult)["total_cost"]
        net = gross - cost
        equity += net
        trades.append(Trade(sc.symbol, direction, str(entry_time), float(entry_price),
                            str(exit_time), float(exit_price), lots, nights,
                            round(gross, 2), round(cost, 2), round(net, 2)))

    for i in range(1, n):
        want = int(target_pos[i - 1])          # decidido no close de i-1
        if want != cur:
            price = open_[i]                     # executa na abertura de i
            if cur != 0:
                close_trade(price, ts[i])
            if want != 0:
                entry_price, entry_time = price, ts[i]
            cur = want
        eq_curve[i] = equity
        if reporter is not None and i % 500 == 0:
            reporter.advance(500, current_file=f"barra {i}/{n} @ {pd.Timestamp(ts[i]).date()}")
    if cur != 0:                                 # fecha posição aberta no fim
        close_trade(close[-1], ts[-1])
        eq_curve[-1] = equity

    wins = [t for t in trades if t.net_usd > 0]
    summary = {
        "symbol": sc.symbol, "n_trades": len(trades),
        "net_usd": round(equity, 2),
        "win_rate": round(len(wins) / len(trades), 3) if trades else None,
        "gross_usd": round(sum(t.gross_usd for t in trades), 2),
        "cost_usd": round(sum(t.cost_usd for t in trades), 2),
        "max_drawdown_usd": round(float((np.maximum.accumulate(eq_curve) - eq_curve).max()), 2),
    }
    return {"trades": [asdict(t) for t in trades], "equity": eq_curve, "summary": summary}
