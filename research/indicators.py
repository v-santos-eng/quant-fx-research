"""Indicadores (Parte 5): ATR de Wilder e ADX. Base do trailing stop e do filtro de
regime do baseline canônico (Parte 13). Todos operam sobre arrays OHLC alinhados.
"""
from __future__ import annotations

import numpy as np


def true_range(high, low, close) -> np.ndarray:
    h, l, c = (np.asarray(x, dtype=float) for x in (high, low, close))
    prev_c = np.empty_like(c)
    prev_c[0] = c[0]
    prev_c[1:] = c[:-1]
    return np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))


def _wilder(x: np.ndarray, n: int) -> np.ndarray:
    """Suavizador de Wilder (forma média): seed = média dos n primeiros; recursivo depois."""
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    seg = x[:n]
    out[n - 1] = np.nanmean(seg) if np.isfinite(seg).any() else np.nan
    for i in range(n, len(x)):
        prev = out[i - 1]
        out[i] = (prev * (n - 1) + x[i]) / n if np.isfinite(prev) else x[i]
    return out


def wilder_atr(high, low, close, n: int = 14) -> np.ndarray:
    """ATR de Wilder (NaN até a barra n-1)."""
    return _wilder(true_range(high, low, close), n)


def adx(high, low, close, n: int = 14) -> np.ndarray:
    """ADX de Wilder em [0, 100] — força de tendência SEM direção (filtro de regime)."""
    h, l, c = (np.asarray(x, dtype=float) for x in (high, low, close))
    up = np.zeros_like(h)
    dn = np.zeros_like(h)
    up[1:] = h[1:] - h[:-1]
    dn[1:] = l[:-1] - l[1:]
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    atr_s = _wilder(true_range(h, l, c), n)
    plus_s = _wilder(plus_dm, n)
    minus_s = _wilder(minus_dm, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        plus_di = 100.0 * plus_s / atr_s
        minus_di = 100.0 * minus_s / atr_s
        dx = 100.0 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    return _wilder(dx, n)
