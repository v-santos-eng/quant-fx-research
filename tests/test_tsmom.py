"""TSMOM: numa tendência de alta o score satura em +1 e o P&L bruto é positivo (fica long);
a banda de drift segura pequenas mudanças de peso."""
import numpy as np
import pandas as pd

from research.tsmom import (_held_with_band, ewma_vol, instrument_pnl, regime_overlay,
                            tsmom_score, tsmom_score_prop)

COST = {"spread_frac": 0.0, "comm_frac": 0.0, "swap_long_frac": 0.0, "swap_short_frac": 0.0}


def _uptrend_d1(n=200, slope=0.5):
    idx = pd.date_range("2015-01-01", periods=n, freq="D")
    close = 100.0 + slope * np.arange(n)          # sobe monotônico
    return pd.DataFrame({"open": close, "high": close, "low": close,
                         "close": close, "volume": 1.0}, index=idx)


def test_score_saturates_up():
    d = _uptrend_d1()
    sc = tsmom_score(d["close"], lookbacks=(21, 63, 126))
    assert sc.iloc[-1] == 1.0                      # todos os horizontes positivos


def test_uptrend_is_long_and_profitable():
    d = _uptrend_d1()
    pnl = instrument_pnl(d, COST, lookbacks=(21, 63, 126))
    assert pnl["gross"].sum() > 0                  # long numa alta -> lucro bruto
    assert pnl["swap"].sum() == 0.0                # custos zerados neste teste


def test_prop_score_positive_and_capped():
    d = _uptrend_d1()
    vol = ewma_vol(d["close"].pct_change(), 32)
    z = tsmom_score_prop(d["close"], vol, cap=2.0)
    assert z.iloc[-1] > 0            # alta -> momentum positivo
    assert z.max() <= 2.0 + 1e-9     # saturado no cap


def test_regime_overlay_scales_down_on_high_vol():
    # série calma seguida de explosão de vol -> overlay reduz exposição no fim
    calm = np.random.default_rng(0).normal(0, 0.001, 600)
    burst = np.random.default_rng(1).normal(0, 0.02, 200)
    r = pd.Series(np.r_[calm, burst], index=pd.date_range("2015-01-01", periods=800))
    ov = regime_overlay(r, vol_win=63, pct_win=504, pct=0.90, scale_down=0.5)
    assert ov.iloc[-1] == 0.5        # regime de vol alta -> exposição reduzida
    assert ov.iloc[300] == 1.0       # regime calmo -> exposição plena


def test_drift_band_holds_small_changes():
    # alvo 1.0 e depois 1.1 (mudança de 10% < banda 20%) -> mantém 1.0
    target = pd.Series([1.0, 1.1, 1.1], index=pd.date_range("2020-01-01", periods=3))
    held = _held_with_band(target, band=0.20)
    assert held.iloc[1] == 1.0
    # mudança grande (1.0 -> 1.5, 50%) rebalanceia
    target2 = pd.Series([1.0, 1.5], index=pd.date_range("2020-01-01", periods=2))
    assert _held_with_band(target2, band=0.20).iloc[1] == 1.5
