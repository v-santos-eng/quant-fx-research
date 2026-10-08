"""Wrapper de pesquisa do MT5 — conecta ao terminal ABERTO, lê specs, amostra
spread/swap ao vivo. Produção real é em MQL5 (Parte 11); isto serve à medição de
custos (Fase 0.3) e coleta. Nunca envia ordens aqui.
"""
from __future__ import annotations

import contextlib
import json
from pathlib import Path

import MetaTrader5 as mt5

SYMBOLS = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "XAUUSD"]
SPECS_OUT = Path("experiments/broker_specs.json")

# SYMBOL_SWAP_MODE (MT5): interpretação de swap_long/short.
SWAP_MODE = {0: "disabled", 1: "points", 2: "symbol_currency", 3: "margin_currency",
             4: "deposit_currency", 5: "interest_current", 6: "interest_open",
             7: "reopen_current", 8: "reopen_bid"}


@contextlib.contextmanager
def mt5_session():
    """Attach ao terminal aberto; garante shutdown. Levanta se não conectar."""
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize falhou: {mt5.last_error()}")
    try:
        yield
    finally:
        mt5.shutdown()


def account_summary() -> dict:
    ai, ti = mt5.account_info(), mt5.terminal_info()
    return {"server": getattr(ai, "server", None), "currency": getattr(ai, "currency", None),
            "demo": getattr(ai, "trade_mode", None) == 0,
            "company": getattr(ti, "company", None), "connected": getattr(ti, "connected", None)}


def symbol_spec(symbol: str) -> dict:
    mt5.symbol_select(symbol, True)
    i = mt5.symbol_info(symbol)
    if i is None:
        return {"symbol": symbol, "error": "symbol_info None"}
    return {"symbol": symbol, "digits": i.digits, "point": i.point,
            "spread_points": i.spread, "contract_size": i.trade_contract_size,
            "tick_value": i.trade_tick_value, "tick_size": i.trade_tick_size,
            "swap_long": i.swap_long, "swap_short": i.swap_short,
            "swap_mode": i.swap_mode, "swap_mode_name": SWAP_MODE.get(i.swap_mode, "?"),
            "swap_rollover3days": i.swap_rollover3days}


def live_spread_points(symbol: str) -> float | None:
    """Spread ao vivo em pontos, ou None se sem quote."""
    t = mt5.symbol_info_tick(symbol)
    i = mt5.symbol_info(symbol)
    if not t or not i or t.ask <= 0 or t.bid <= 0:
        return None
    return round((t.ask - t.bid) / i.point, 1)


def snapshot(symbols: list[str] = SYMBOLS) -> dict:
    """Captura conta + specs (inclui swap medido) para experiments/broker_specs.json."""
    with mt5_session():
        out = {"account": account_summary(),
               "symbols": {s: symbol_spec(s) for s in symbols}}
    SPECS_OUT.parent.mkdir(parents=True, exist_ok=True)
    SPECS_OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    snap = snapshot()
    acc = snap["account"]
    print(f"conta: {acc['server']} {acc['currency']} demo={acc['demo']}", flush=True)
    for s, spec in snap["symbols"].items():
        print(f"{s}: swap L/S={spec.get('swap_long')}/{spec.get('swap_short')} "
              f"mode={spec.get('swap_mode_name')} triple={spec.get('swap_rollover3days')} "
              f"spread_pts={spec.get('spread_points')}", flush=True)
    print(f"WROTE {SPECS_OUT}", flush=True)
