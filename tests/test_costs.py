import pytest

from research.costs import (
    SymbolCost,
    commission_cost_usd,
    notional_usd,
    pip_value_usd,
    round_trip_cost_usd,
    spread_cost_usd,
    swap_pnl_usd,
)

EURUSD = SymbolCost("EURUSD", pip=1e-4, point=1e-5, contract=100_000,
                    commission_per_million_usd=35.0, swap_long_points=-18.62, swap_short_points=8.32)
USDJPY = SymbolCost("USDJPY", pip=1e-2, point=1e-3, contract=100_000,
                    commission_per_million_usd=35.0, swap_long_points=30.57, swap_short_points=-45.33)


def test_pip_value_quote_usd_constant():
    assert pip_value_usd(EURUSD, 1.14) == pytest.approx(10.0)  # 1e-4 * 1e5
    assert pip_value_usd(EURUSD, 0.90) == pytest.approx(10.0)  # independe do preço


def test_pip_value_base_usd_price_dependent():
    assert pip_value_usd(USDJPY, 100.0) == pytest.approx(10.0)   # 1e-2*1e5/100
    assert pip_value_usd(USDJPY, 163.0) == pytest.approx(6.1349, rel=1e-3)


def test_notional():
    assert notional_usd(EURUSD, 1.14, 1.0) == pytest.approx(114_000)   # quote USD
    assert notional_usd(USDJPY, 163.0, 1.0) == pytest.approx(100_000)  # base USD


def test_commission_roundtrip():
    # 35/M * 114k/1M * 2 lados = 7.98
    assert commission_cost_usd(EURUSD, 1.14, 1.0) == pytest.approx(7.98)


def test_spread_cost_and_slippage():
    base = spread_cost_usd(EURUSD, 0.30, 1.14, 1.0)
    assert base == pytest.approx(0.30 * 10.0)          # 0.30 pip * $10
    stressed = spread_cost_usd(EURUSD, 0.30, 1.14, 1.0, slippage_mult=1.0)
    assert stressed == pytest.approx(2 * base)         # +1 spread de slippage


def test_all_in_eurusd_sanity_pips():
    """Âncora: EURUSD all-in ~1,06 pip (Parte 3). spread 0,30 + comissão ~0,80."""
    rt = round_trip_cost_usd(EURUSD, spread_pips=0.30, price=1.14, lots=1.0, direction="long")
    pip_val = pip_value_usd(EURUSD, 1.14)
    all_in_pips = (rt["spread"] + rt["commission"]) / pip_val  # sem swap (0 noites)
    assert 1.0 <= all_in_pips <= 1.2


def test_swap_debit_and_credit():
    debit = swap_pnl_usd(EURUSD, "long", nights=1, price=1.14, lots=1.0)
    assert debit == pytest.approx(-18.62)              # -18.62 pts * $1/ponto
    credit = swap_pnl_usd(EURUSD, "short", nights=1, price=1.14, lots=1.0)
    assert credit == pytest.approx(8.32)
    # swap débito ENTRA como custo (total sobe)
    rt = round_trip_cost_usd(EURUSD, 0.30, 1.14, 1.0, "long", nights=3)
    assert rt["total_cost"] == pytest.approx(0.30 * 10 + 7.98 - (-18.62 * 3))
