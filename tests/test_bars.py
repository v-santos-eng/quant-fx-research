import numpy as np
import pandas as pd
import pytest

from research.bars import build_bars


def _ticks(n=16, start="2020-01-01", freq="30min"):
    ts = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    mid = 1.1000 + 0.0001 * np.arange(n)
    return pd.DataFrame({"timestamp": ts, "bid": mid - 5e-5, "ask": mid + 5e-5})


def test_h4_ohlc_two_bars():
    bars = build_bars(_ticks(), "4h", price="mid")
    assert len(bars) == 2
    b0 = bars.iloc[0]
    assert b0["timestamp"] == pd.Timestamp("2020-01-01 00:00", tz="UTC")
    assert b0["open"] == pytest.approx(1.1000)
    assert b0["high"] == pytest.approx(1.1007)
    assert b0["low"] == pytest.approx(1.1000)
    assert b0["close"] == pytest.approx(1.1007)
    assert b0["volume"] == 8
    assert bars.iloc[1]["open"] == pytest.approx(1.1008)
    assert bars.iloc[1]["close"] == pytest.approx(1.1015)


def test_price_bid_vs_ask():
    ticks = _ticks(n=8)
    bid_bars = build_bars(ticks, "4h", price="bid")
    ask_bars = build_bars(ticks, "4h", price="ask")
    assert ask_bars.iloc[0]["open"] - bid_bars.iloc[0]["open"] == pytest.approx(1e-4)


def test_origin_offset_shifts_alignment():
    # offset de 2h -> barras 4h alinham a 02,06,10... em vez de 00,04,08
    ticks = _ticks(n=16)
    shifted = build_bars(ticks, "4h", origin_offset=pd.Timedelta("2h"))
    assert shifted.iloc[0]["timestamp"] == pd.Timestamp("2019-12-31 22:00", tz="UTC")


def test_weekend_gap_no_empty_bars():
    # dois blocos de ticks separados por um vão grande -> sem barras vazias no meio
    a = _ticks(n=4, start="2020-01-03 20:00")  # sexta
    b = _ticks(n=4, start="2020-01-05 22:00")  # domingo à noite
    bars = build_bars(pd.concat([a, b], ignore_index=True), "4h")
    assert bars["volume"].min() > 0
    assert len(bars) == 2


def test_empty_input():
    empty = pd.DataFrame({"timestamp": pd.to_datetime([]).tz_localize("UTC"),
                          "bid": [], "ask": []})
    assert build_bars(empty, "4h").empty


def test_invalid_price_raises():
    with pytest.raises(ValueError):
        build_bars(_ticks(n=4), "4h", price="close")
