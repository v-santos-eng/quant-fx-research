"""Mecânica da reversão: preço estica abaixo do VWAP -> fade LONG -> alvo na volta ao VWAP."""
import pandas as pd

from research.costs import SymbolCost
from research.meanrev import MRParams, mr_trades

SC = SymbolCost("TEST", pip=1.0, point=0.001, contract=1.0,
                commission_per_million_usd=0.0, swap_long_points=0.0, swap_short_points=0.0)
# z baixo p/ disparar fácil; stop grande p/ não bindar; atr_n=2 p/ ATR finito cedo; warmup 30min.
P = MRParams(z=1.0, stop_atr=100.0, warmup_min=30, tf_min=15, atr_n=2)


def _bar(t, o, h, l, c, v=100.0):
    return {"timestamp": pd.Timestamp(t, tz="UTC"), "open": o, "high": h, "low": l,
            "close": c, "volume": v}


def test_fade_long_reverts_to_vwap():
    rows = [
        _bar("2024-06-04 07:00", 100.0, 100.0, 100.0, 100.0),  # VWAP ~100
        _bar("2024-06-04 07:15", 100.0, 100.0, 100.0, 100.0),  # fim do warmup (2 barras)
        _bar("2024-06-04 07:30", 100.0, 100.0, 97.0, 97.0),    # estica p/ baixo -> fade LONG
        _bar("2024-06-04 07:45", 97.0, 98.0, 97.0, 98.0),      # entrada @open=97
        _bar("2024-06-04 08:00", 98.0, 99.5, 98.0, 99.0),      # sobe e cruza o VWAP -> alvo
        _bar("2024-06-04 08:15", 99.0, 99.2, 98.5, 98.7),
        _bar("2024-06-04 08:30", 98.7, 99.0, 98.3, 98.6),
        _bar("2024-06-04 08:45", 98.6, 98.9, 98.2, 98.5),
    ]
    res = mr_trades(pd.DataFrame(rows), "07:00-09:00", SC, spread_by_hour={}, params=P, lots=1.0)
    ts = res["trades"]
    assert len(ts) == 1, res["summary"]
    t = ts[0]
    assert t["direction"] == "long"          # fade de baixo = compra
    assert t["entry_price"] == 97.0          # abertura da barra seguinte ao gatilho
    assert t["gross_usd"] > 0                # reverteu ao VWAP -> ganho
    assert t["nights"] == 0


def test_no_extension_no_trade():
    # preço cola no VWAP, nunca estica z*ATR -> nenhum trade
    rows = [_bar(f"2024-06-04 0{7 + i // 4}:{15 * (i % 4):02d}", 100.0, 100.1, 99.9, 100.0)
            for i in range(8)]
    res = mr_trades(pd.DataFrame(rows), "07:00-09:00", SC, spread_by_hour={}, params=P)
    assert res["trades"] == []
