import numpy as np
import pandas as pd
import pytest

from research.backtester import (
    _swap_nights,
    canonical_positions,
    donchian_positions,
    simulate,
)
from research.costs import SymbolCost

# EURUSD sem custos -> P&L bruto exato
EUR_FREE = SymbolCost("EURUSD", pip=1e-4, point=1e-5, contract=100_000,
                      commission_per_million_usd=0.0, swap_long_points=0.0, swap_short_points=0.0)
EUR = SymbolCost("EURUSD", pip=1e-4, point=1e-5, contract=100_000,
                 commission_per_million_usd=35.0, swap_long_points=0.0, swap_short_points=0.0)


def _bars(opens, closes=None, highs=None, lows=None, start="2020-01-01", freq="1D"):
    n = len(opens)
    ts = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    closes = opens if closes is None else closes
    highs = [max(o, c) for o, c in zip(opens, closes)] if highs is None else highs
    lows = [min(o, c) for o, c in zip(opens, closes)] if lows is None else lows
    return pd.DataFrame({"timestamp": ts, "open": opens, "high": highs,
                         "low": lows, "close": closes, "volume": [1] * n})


def test_long_gross_pnl_no_costs():
    bars = _bars([1.1000, 1.1010, 1.1020, 1.1030])
    pos = np.array([1, 1, 0, 0], dtype=np.int8)  # entra open[1]=1.1010, sai open[3]=1.1030
    out = simulate(bars, pos, EUR_FREE, spread_pips=0.0, lots=0.1)
    assert out["summary"]["n_trades"] == 1
    t = out["trades"][0]
    assert t["direction"] == "long"
    assert t["entry_price"] == pytest.approx(1.1010)
    assert t["exit_price"] == pytest.approx(1.1030)
    assert t["gross_usd"] == pytest.approx(20.0)   # 20 pips * $10 * 0.1 lote
    assert t["net_usd"] == pytest.approx(20.0)      # sem custos


def test_short_gross_pnl():
    bars = _bars([1.1030, 1.1020, 1.1010, 1.1000])
    pos = np.array([-1, -1, 0, 0], dtype=np.int8)
    out = simulate(bars, pos, EUR_FREE, spread_pips=0.0, lots=0.1)
    t = out["trades"][0]
    assert t["direction"] == "short"
    assert t["gross_usd"] == pytest.approx(20.0)   # caiu 20 pips vendido = +$20


def test_costs_reduce_net():
    bars = _bars([1.1000, 1.1010, 1.1020, 1.1030])
    pos = np.array([1, 1, 0, 0], dtype=np.int8)
    out = simulate(bars, pos, EUR, spread_pips=0.30, lots=0.1)
    t = out["trades"][0]
    # spread 0.3pip*$10*0.1=$0.30 ; comissão 35*(0.1*1e5*1.1010)/1e6*2=$0.77
    assert t["cost_usd"] == pytest.approx(0.30 + 0.77, abs=0.02)
    assert t["net_usd"] == pytest.approx(20.0 - t["cost_usd"], abs=0.01)


def test_open_position_closed_at_end():
    bars = _bars([1.1000, 1.1010, 1.1020, 1.1030])
    pos = np.array([1, 1, 1, 1], dtype=np.int8)  # nunca sai -> fecha no último close
    out = simulate(bars, pos, EUR_FREE, spread_pips=0.0, lots=0.1)
    assert out["summary"]["n_trades"] == 1
    assert out["trades"][0]["exit_price"] == pytest.approx(1.1030)


def test_swap_nights_wednesday_triple_and_weekend():
    import pandas as pd
    mon, wed, thu, fri = ("2020-01-06", "2020-01-08", "2020-01-09", "2020-01-10")
    # semana cheia seg->seg = 7 rollovers (qua conta 3, sáb/dom 0)
    assert _swap_nights(pd.Timestamp(mon, tz="UTC"), pd.Timestamp("2020-01-13", tz="UTC")) == 7
    # noite de quarta = ×3
    assert _swap_nights(pd.Timestamp(wed, tz="UTC"), pd.Timestamp(thu, tz="UTC")) == 3
    # sexta->segunda = só a sexta (fim de semana sem rollover)
    assert _swap_nights(pd.Timestamp(fri, tz="UTC"), pd.Timestamp("2020-01-13", tz="UTC")) == 1
    # mesmo dia = 0
    assert _swap_nights(pd.Timestamp(mon, tz="UTC"), pd.Timestamp(mon, tz="UTC")) == 0


def test_canonical_enters_trend_exits_flat_on_reversal():
    chop = 100 + np.zeros(60)                       # sem tendência (ADX baixo) -> flat
    up = 100 + np.arange(1, 61, dtype=float)        # tendência forte -> entra comprado
    down = up[-1] - np.arange(1, 41, dtype=float) * 1.5  # reversão -> trailing stop sai
    close = np.concatenate([chop, up, down])
    n = len(close)
    ts = pd.date_range("2020-01-01", periods=n, freq="4h", tz="UTC")
    bars = pd.DataFrame({"timestamp": ts, "open": close, "high": close + 0.3,
                         "low": close - 0.3, "close": close, "volume": np.ones(n)})
    pos = canonical_positions(bars, entry_n=20, atr_n=14, atr_mult=3.0, adx_n=14, adx_min=18.0)
    assert (pos == 1).any()                     # entrou comprado durante a tendência
    assert (pos[:40] == 0).all()                # ficou flat no chop inicial (pós-warmup)
    first_long = int(np.argmax(pos == 1))
    assert (pos[first_long:] != 1).any()        # saiu do long (trailing stop) em algum momento


def test_donchian_breakout_long_and_exit():
    close = [1.10] * 5 + [1.20, 1.20, 1.05]     # rompe pra cima e depois despenca
    bars = _bars(close, closes=close)
    pos = donchian_positions(bars, entry_n=4, exit_n=2)
    assert pos[5] == 1        # close 1.20 > canal superior -> long
    assert pos[-1] == -1      # despencou abaixo do canal inferior -> vira short
