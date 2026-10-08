"""Monte Carlo de robustez (Fase 0.5, Parte 8). Três eixos:

  1. BLOCK BOOTSTRAP da sequência de trades -> distribuição de drawdown e tempo
     submerso (preserva autocorrelação por blocos). O percentil 99 do drawdown
     alimenta o circuit breaker (RF-12).
  2. PERTURBAÇÃO de parâmetros ±20% -> se a métrica colapsa, otimizou-se um pico,
     não um platô.
  3. STRESS de custos (spread ×2, slippage 1-2 spreads, swap ×2) -> aplicado no
     re-backtest; aqui ficam os multiplicadores de referência.
"""
from __future__ import annotations

import numpy as np

# Multiplicadores de stress de custo (Parte 8). Aplicados no re-backtest da Fase 1/4.
COST_STRESS = {"spread_mult": 2.0, "swap_mult": 2.0, "slippage_spreads": 2.0}


def max_drawdown(equity) -> float:
    """Drawdown máximo (pico-a-vale) em unidades de equity. Sempre >= 0."""
    e = np.asarray(equity, dtype=float)
    if e.size == 0:
        return 0.0
    return float((np.maximum.accumulate(e) - e).max())


def time_underwater(equity) -> int:
    """Maior nº de passos consecutivos abaixo de um pico anterior (tempo submerso)."""
    e = np.asarray(equity, dtype=float)
    peak = np.maximum.accumulate(e)
    best = cur = 0
    for below in e < peak:
        cur = cur + 1 if below else 0
        best = max(best, cur)
    return best


def block_bootstrap(pnl, block_size: int, n_sims: int, rng=None) -> np.ndarray:
    """Reamostra blocos contíguos do P&L por trade e devolve `n_sims` curvas de equity
    (soma acumulada), cada uma do mesmo tamanho da série original.
    """
    rng = rng or np.random.default_rng()
    pnl = np.asarray(pnl, dtype=float)
    n = len(pnl)
    if n == 0:
        return np.zeros((n_sims, 0))
    n_blocks = int(np.ceil(n / block_size))
    start_hi = max(n - block_size, 0)
    paths = np.empty((n_sims, n))
    for s in range(n_sims):
        starts = rng.integers(0, start_hi + 1, size=n_blocks)
        seq = np.concatenate([pnl[st:st + block_size] for st in starts])[:n]
        paths[s] = np.cumsum(seq)
    return paths


def mc_distribution(pnl, block_size: int = 10, n_sims: int = 1000,
                    percentiles=(50, 95, 99), rng=None) -> dict:
    """Distribuição de drawdown máximo e tempo submerso via block bootstrap."""
    paths = block_bootstrap(pnl, block_size, n_sims, rng)
    dds = np.array([max_drawdown(p) for p in paths])
    tuw = np.array([time_underwater(p) for p in paths])
    return {
        "n_sims": n_sims, "block_size": block_size,
        "max_drawdown": {f"p{q}": float(np.percentile(dds, q)) for q in percentiles},
        "time_underwater": {f"p{q}": float(np.percentile(tuw, q)) for q in percentiles},
    }


def param_sensitivity(metric_fn, base_params: dict, pct: float = 0.20) -> dict:
    """Perturba cada parâmetro numérico em ±pct e mede a métrica. Colapso = pico, não platô."""
    out = {"base": float(metric_fn(base_params)), "pct": pct, "perturbations": {}}
    for k, v in base_params.items():
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            continue
        low = {**base_params, k: type(v)(v * (1 - pct))}
        high = {**base_params, k: type(v)(v * (1 + pct))}
        out["perturbations"][k] = {"low": float(metric_fn(low)), "high": float(metric_fn(high))}
    return out
