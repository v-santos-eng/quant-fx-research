import numpy as np
import pandas as pd
import pytest

from research.sanity import (
    QualityReport,
    detect_gaps,
    detect_spikes,
    drop_invalid_quotes,
    normalize_to_utc,
    quality_report,
)


def _ticks(timestamps, bids, asks):
    return pd.DataFrame({"timestamp": timestamps, "bid": bids, "ask": asks})


def test_missing_columns_raises():
    with pytest.raises(ValueError):
        detect_gaps(pd.DataFrame({"timestamp": []}), pd.Timedelta("1s"))


def test_normalize_naive_to_utc():
    df = _ticks(pd.to_datetime(["2020-01-01 10:00", "2020-01-01 12:00"]), [1.0, 1.0], [1.1, 1.1])
    out = normalize_to_utc(df, source_tz="Europe/London")  # GMT em janeiro -> UTC igual
    assert str(out["timestamp"].dt.tz) == "UTC"
    assert out["timestamp"].iloc[0].hour == 10


def test_normalize_dst_offset():
    # Julho: Londres = UTC+1, então 10:00 local -> 09:00 UTC
    df = _ticks(pd.to_datetime(["2020-07-01 10:00"]), [1.0], [1.1])
    out = normalize_to_utc(df, source_tz="Europe/London")
    assert out["timestamp"].iloc[0].hour == 9


def test_detect_gaps_finds_hole():
    ts = pd.to_datetime(["2020-01-01 10:00:00", "2020-01-01 10:00:01",
                         "2020-01-01 10:05:00"])  # buraco de ~5min
    df = _ticks(ts, [1.0, 1.0, 1.0], [1.1, 1.1, 1.1])
    gaps = detect_gaps(df, max_gap=pd.Timedelta("1min"))
    assert len(gaps) == 1
    assert gaps["duration"].iloc[0] >= pd.Timedelta("4min")


def test_detect_gaps_none_when_dense():
    ts = pd.date_range("2020-01-01 10:00:00", periods=100, freq="1s")
    df = _ticks(ts, np.ones(100), np.ones(100) * 1.1)
    assert len(detect_gaps(df, max_gap=pd.Timedelta("10s"))) == 0


def test_detect_spikes_flags_injected_spike():
    n = 200
    ts = pd.date_range("2020-01-01", periods=n, freq="1s")
    bid = np.full(n, 1.1000)
    bid += np.random.default_rng(0).normal(0, 1e-5, n)  # ruído pequeno
    bid[100] = 1.1500  # spike isolado que reverte
    df = _ticks(ts, bid, bid + 1e-4)
    spikes = detect_spikes(df, k=8.0, window=50)
    assert 100 in spikes


def test_quality_report_counts():
    ts = pd.to_datetime(["2020-01-01 10:00:00", "2020-01-01 10:00:00",  # dup
                         "2020-01-01 10:10:00"])                        # gap
    df = _ticks(ts, [1.10, -1.0, 1.10], [1.11, 1.11, 1.09])            # nonpos + crossed
    rep = quality_report(df, max_gap=pd.Timedelta("1min"))
    assert isinstance(rep, QualityReport)
    assert rep.n_ticks == 3
    assert rep.n_dup_timestamps == 1
    assert rep.n_nonpositive == 1
    assert rep.n_crossed == 1        # terceira linha: bid 1.10 > ask 1.09
    assert rep.n_gaps == 1


def test_drop_invalid_quotes():
    ts = pd.to_datetime(["2020-01-01 10:00:00"] * 4)
    df = _ticks(ts, [1.10, 1.11, -1.0, 1.10], [1.11, 1.10, 1.11, 1.09])
    #                 ok    cruzado nonpos  cruzado
    out = drop_invalid_quotes(df)
    assert len(out) == 1
    assert out["bid"].iloc[0] == 1.10 and out["ask"].iloc[0] == 1.11


def test_quality_report_empty():
    rep = quality_report(_ticks(pd.to_datetime([]), [], []), max_gap=pd.Timedelta("1min"))
    assert rep.n_ticks == 0
