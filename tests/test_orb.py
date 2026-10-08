"""Teste da mecânica do baseline ORB: gatilho após OR, filtro VWAP, entrada na abertura
seguinte, stop no lado oposto do OR, alvo 2R batido intrabar pelo high."""
import pandas as pd

from research.costs import SymbolCost
from research.orb import ORBParams, orb_dataset, orb_trades

SC = SymbolCost("TEST", pip=1.0, point=0.001, contract=1.0,
                commission_per_million_usd=0.0, swap_long_points=0.0, swap_short_points=0.0)
# atr_mult grande => quem manda no stop é o lado oposto do OR; k_range=0 desliga filtro de range;
# atr_n=2 => ATR fica finito cedo (série curta de teste).
P = ORBParams(or_min=30, tf_min=15, atr_mult=100.0, r_mult=2.0, k_range=0.0, atr_n=2)


def _bar(t, o, h, l, c, v=100.0):
    return {"timestamp": pd.Timestamp(t, tz="UTC"), "open": o, "high": h, "low": l,
            "close": c, "volume": v}


def test_orb_long_hits_target():
    rows = [
        _bar("2024-06-04 07:00", 100.5, 101.0, 100.0, 100.5),  # OR
        _bar("2024-06-04 07:15", 100.5, 101.0, 100.2, 100.6),  # OR  -> hi=101 lo=100
        _bar("2024-06-04 07:30", 100.6, 101.2, 100.5, 100.8),  # sem rompimento
        _bar("2024-06-04 07:45", 100.8, 102.0, 100.7, 101.5),  # gatilho long (close>101 e >vwap)
        _bar("2024-06-04 08:00", 101.5, 102.0, 101.4, 101.8),  # entrada @open=101.5
        _bar("2024-06-04 08:15", 101.8, 104.6, 101.7, 104.0),  # high>=alvo 104.5 -> sai no alvo
        _bar("2024-06-04 08:30", 104.0, 104.2, 103.5, 103.8),
        _bar("2024-06-04 08:45", 103.8, 104.0, 103.5, 103.7),  # última barra da sessão
    ]
    bars = pd.DataFrame(rows)
    res = orb_trades(bars, "07:00-09:00", SC, spread_by_hour={}, params=P, lots=1.0)
    ts = res["trades"]
    assert len(ts) == 1, res["summary"]
    t = ts[0]
    assert t["direction"] == "long"
    assert t["entry_price"] == 101.5           # abertura da barra seguinte ao gatilho
    # stop=100.0 (OR_low), risco=1.5, alvo=101.5+2*1.5=104.5
    assert t["exit_price"] == 104.5
    assert t["gross_usd"] == 3.0               # (104.5-101.5)*1.0*1 lote
    assert t["nights"] == 0                     # intraday => swap nunca


def test_orb_no_trigger_no_trade():
    # preço nunca rompe o OR -> nenhum trade
    rows = [_bar(f"2024-06-04 0{7 + i // 4}:{15 * (i % 4):02d}", 100.5, 100.9, 100.1, 100.5)
            for i in range(8)]
    res = orb_trades(pd.DataFrame(rows), "07:00-09:00", SC, spread_by_hour={}, params=P)
    assert res["trades"] == []


def test_orb_dataset_contract():
    # o dataset do meta-label expõe as 8 features + direction + rótulo y coerente com net
    rows = [
        _bar("2024-06-04 07:00", 100.5, 101.0, 100.0, 100.5),
        _bar("2024-06-04 07:15", 100.5, 101.0, 100.2, 100.6),
        _bar("2024-06-04 07:30", 100.6, 101.2, 100.5, 100.8),
        _bar("2024-06-04 07:45", 100.8, 102.0, 100.7, 101.5),
        _bar("2024-06-04 08:00", 101.5, 102.0, 101.4, 101.8),
        _bar("2024-06-04 08:15", 101.8, 104.6, 101.7, 104.0),
        _bar("2024-06-04 08:30", 104.0, 104.2, 103.5, 103.8),
        _bar("2024-06-04 08:45", 103.8, 104.0, 103.5, 103.7),
    ]
    ds = orb_dataset(pd.DataFrame(rows), "07:00-09:00", SC, spread_by_hour={}, params=P, lots=1.0)
    assert len(ds) == 1
    for col in ("or_width_atr", "dist_vwap_atr", "atr_regime", "minute_of_session",
                "prev_day_ret", "h1_slope_atr", "or_vol_ratio", "dow", "direction", "y", "net_usd"):
        assert col in ds.columns
    row = ds.iloc[0]
    assert row["y"] == int(row["net_usd"] > 0)   # rótulo coerente com o desfecho líquido
    assert row["direction"] == 1                  # trade long
