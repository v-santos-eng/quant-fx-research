"""Modelo de custo aplicado ao fill (Fase 0.4): spread + comissão + swap + slippage,
convertidos para USD por par. Todos os pares do portfólio têm USD num lado (sem
cross), então a conversão é fechada:

- Quote = USD (EURUSD, GBPUSD, AUDUSD, XAUUSD): pip vale `pip*contract` USD (constante).
- Base  = USD (USDJPY, USDCAD): pip vale `pip*contract/preço` USD (depende do preço).

Caminho de dinheiro — ver test_costs.py (âncora: all-in EURUSD ~1,06 pip, Parte 3).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SymbolCost:
    symbol: str
    pip: float
    point: float
    contract: float
    commission_per_million_usd: float
    swap_long_points: float
    swap_short_points: float


def _base_is_usd(symbol: str) -> bool:
    return symbol.startswith("USD")


def pip_value_usd(sc: SymbolCost, price: float) -> float:
    """Valor de 1 pip por 1 lote, em USD."""
    if _base_is_usd(sc.symbol):          # USDJPY, USDCAD
        return sc.pip * sc.contract / price
    return sc.pip * sc.contract          # EURUSD, GBPUSD, AUDUSD, XAUUSD


def notional_usd(sc: SymbolCost, price: float, lots: float) -> float:
    """Volume negociado em USD (base p/ comissão)."""
    if _base_is_usd(sc.symbol):
        return lots * sc.contract
    return lots * sc.contract * price


def spread_cost_usd(sc: SymbolCost, spread_pips: float, price: float, lots: float,
                    slippage_mult: float = 0.0) -> float:
    """Custo de spread round-trip (+ slippage de stress) em USD. Sempre >= 0."""
    return spread_pips * (1.0 + slippage_mult) * pip_value_usd(sc, price) * lots


def commission_cost_usd(sc: SymbolCost, price: float, lots: float, sides: int = 2) -> float:
    """Comissão ECN em USD. sides=2 = abertura + fechamento (round-trip)."""
    return sc.commission_per_million_usd * notional_usd(sc, price, lots) / 1_000_000 * sides


def swap_pnl_usd(sc: SymbolCost, direction: str, nights: int, price: float, lots: float) -> float:
    """Swap acumulado em USD (P&L: negativo = débito, positivo = crédito).

    Modo 'points' do MT5: valor = pontos * valor_do_ponto * lotes * noites.
    (Dia triplo de quarta não modelado aqui; entra no agendador de noites do backtester.)
    """
    pts = sc.swap_long_points if direction == "long" else sc.swap_short_points
    point_value = pip_value_usd(sc, price) * (sc.point / sc.pip)
    return pts * point_value * lots * nights


def round_trip_cost_usd(sc: SymbolCost, spread_pips: float, price: float, lots: float,
                        direction: str, nights: int = 0, slippage_mult: float = 0.0) -> dict:
    """Custo total de um trade round-trip em USD, com breakdown.

    total_cost = spread + comissão - swap_pnl  (swap crédito reduz o custo).
    """
    spread = spread_cost_usd(sc, spread_pips, price, lots, slippage_mult)
    comm = commission_cost_usd(sc, price, lots)
    swap = swap_pnl_usd(sc, direction, nights, price, lots)
    return {"spread": spread, "commission": comm, "swap_pnl": swap,
            "total_cost": spread + comm - swap}
