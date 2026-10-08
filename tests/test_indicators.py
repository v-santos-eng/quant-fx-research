import numpy as np

from research.indicators import adx, true_range, wilder_atr


def test_true_range_constant():
    high = np.array([10, 11, 12, 13.0])
    low = np.array([8, 9, 10, 11.0])
    close = np.array([9, 10, 11, 12.0])
    tr = true_range(high, low, close)
    # range 2 e close anterior dentro do range -> TR = 2 em todas
    assert np.all(tr == 2.0)


def test_atr_converges_to_constant_range():
    n = 200
    high = np.full(n, 12.0) + np.arange(n) * 0.0
    low = high - 2.0
    close = high - 1.0
    atr = wilder_atr(high, low, close, n=14)
    assert abs(atr[-1] - 2.0) < 0.1        # range constante de 2 -> ATR -> 2


def test_adx_high_in_strong_trend():
    n = 300
    close = np.arange(n, dtype=float)          # tendência forte e monotônica
    high = close + 0.5
    low = close - 0.5
    a = adx(high, low, close, n=14)
    assert np.nanmax(a) > 40.0                  # ADX alto em tendência forte
    assert np.nanmax(a) <= 100.0 + 1e-9


def test_adx_low_in_chop():
    rng = np.random.default_rng(0)
    n = 500
    close = 100 + np.cumsum(rng.normal(0, 0.01, n))  # quase parado / ruído
    high = close + rng.uniform(0.05, 0.15, n)
    low = close - rng.uniform(0.05, 0.15, n)
    a = adx(high, low, close, n=14)
    assert np.nanmean(a[50:]) < 40.0            # sem tendência -> ADX baixo/médio
