import lzma
import struct
from datetime import datetime

import pandas as pd

from research.acquisition import (
    bi5_decode,
    dukascopy_url,
    write_parquet_versioned,
)

_REC = struct.Struct(">iiiff")


def _make_bi5(records) -> bytes:
    """records: lista de (ms, ask_pts, bid_pts). Comprime como a Dukascopy (LZMA alone)."""
    raw = b"".join(_REC.pack(ms, ask, bid, 1.0, 1.0) for ms, ask, bid in records)
    return lzma.compress(raw, format=lzma.FORMAT_ALONE)


def test_url_month_is_zero_indexed():
    url = dukascopy_url("EURUSD", datetime(2020, 3, 15, 9))  # março -> "02"
    assert url.endswith("EURUSD/2020/02/15/09h_ticks.bi5")


def test_bi5_decode_roundtrip():
    raw = _make_bi5([(0, 110500, 110480), (1500, 110510, 110490)])
    df = bi5_decode(raw, "EURUSD", datetime(2020, 1, 1, 10))
    assert list(df.columns) == ["timestamp", "bid", "ask"]
    assert len(df) == 2
    assert abs(df["ask"].iloc[0] - 1.10500) < 1e-9
    assert abs(df["bid"].iloc[0] - 1.10480) < 1e-9
    assert str(df["timestamp"].dt.tz) == "UTC"
    assert df["timestamp"].iloc[1] == pd.Timestamp("2020-01-01 10:00:01.500", tz="UTC")


def test_bi5_decode_jpy_point_value():
    raw = _make_bi5([(0, 108250, 108240)])  # USDJPY: /1e3 -> 108.25
    df = bi5_decode(raw, "USDJPY", datetime(2020, 1, 1, 0))
    assert abs(df["ask"].iloc[0] - 108.250) < 1e-6


def test_bi5_decode_empty():
    assert len(bi5_decode(b"", "EURUSD", datetime(2020, 1, 1, 0))) == 0


def test_write_parquet_versioned(tmp_path):
    df = bi5_decode(_make_bi5([(0, 110500, 110480)]), "EURUSD", datetime(2020, 1, 1, 10))
    path, digest = write_parquet_versioned(df, tmp_path, "EURUSD_2020")
    assert path.exists()
    assert len(digest) == 64
    back = pd.read_parquet(path)
    assert len(back) == 1
    assert abs(back["ask"].iloc[0] - 1.10500) < 1e-9
