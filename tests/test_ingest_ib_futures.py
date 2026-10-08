"""Testa a normalização pura das barras do IB (offline, sem conexão) e a integridade do universo."""
import pandas as pd

from research.ingest_ib_futures import UNIVERSE, _norm_df


def test_norm_df_schema_and_utc():
    raw = pd.DataFrame({
        "date": ["2020-01-02", "2020-01-03"],
        "open": [3200.0, 3230.0], "high": [3260.0, 3240.0],
        "low": [3190.0, 3200.0], "close": [3250.0, 3235.0], "volume": [1_000_000, 900_000],
    })
    out = _norm_df(raw)
    assert list(out.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert str(out["timestamp"].dt.tz) == "UTC"
    assert out["close"].tolist() == [3250.0, 3235.0]


def test_norm_df_empty():
    assert _norm_df(pd.DataFrame()).empty
    assert list(_norm_df(None).columns) == ["timestamp", "open", "high", "low", "close", "volume"]


def test_universe_covers_sectors():
    sectors = {v[3] for v in UNIVERSE.values()}
    assert sectors >= {"index", "metal", "energy", "fx", "rates", "ag"}  # breadth cross-asset
    assert len(UNIVERSE) >= 18
