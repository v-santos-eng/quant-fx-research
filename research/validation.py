"""Toolkit de validação estatística (Fase 0.5) — Sharpe honesto sob múltiplos testes.

Todos os Sharpe aqui são POR PERÍODO (não anualizados) e na mesma escala entre si.
Referências: Lo (2002) erro padrão do Sharpe; Bailey & López de Prado (2014) PSR/DSR.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import kurtosis as _kurtosis
from scipy.stats import norm
from scipy.stats import skew as _skew

EULER_GAMMA = 0.5772156649015329


def sharpe_ratio(returns, periods_per_year: float | None = None) -> float:
    """Sharpe da série. Anualiza por sqrt(periods_per_year) se informado."""
    r = np.asarray(returns, dtype=float)
    sr = r.mean() / r.std(ddof=1)
    return float(sr * np.sqrt(periods_per_year)) if periods_per_year else float(sr)


def sharpe_std_error(sr: float, n: int) -> float:
    """Erro padrão do Sharpe (Lo 2002, IID). sr e SE na mesma escala (por período)."""
    return float(np.sqrt((1.0 + 0.5 * sr**2) / n))


def probabilistic_sharpe_ratio(returns, sr_benchmark: float = 0.0) -> float:
    """PSR = P(Sharpe verdadeiro > sr_benchmark) dado o histórico; corrige skew/kurtose.

    returns: série de retornos por período. Retorna probabilidade em [0, 1].
    """
    r = np.asarray(returns, dtype=float)
    n = len(r)
    sr = r.mean() / r.std(ddof=1)
    g3 = float(_skew(r, bias=False))
    g4 = float(_kurtosis(r, fisher=False, bias=False))  # Pearson: normal = 3
    denom = np.sqrt(1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr**2)
    return float(norm.cdf((sr - sr_benchmark) * np.sqrt(n - 1) / denom))


def expected_max_sharpe(sr_variance: float, n_trials: int) -> float:
    """Sharpe máximo esperado sob `n_trials` ensaios de puro ruído (Bailey/LdP)."""
    if n_trials < 2:
        return 0.0
    return float(np.sqrt(sr_variance) * (
        (1.0 - EULER_GAMMA) * norm.ppf(1.0 - 1.0 / n_trials)
        + EULER_GAMMA * norm.ppf(1.0 - 1.0 / (n_trials * np.e))))


def deflated_sharpe_ratio(returns, sr_variance: float, n_trials: int) -> float:
    """DSR = PSR com benchmark = Sharpe máximo esperado de `n_trials` (deflaciona
    múltiplos testes). `sr_variance` = variância dos Sharpe dos ensaios (do attempt log).
    """
    sr_star = expected_max_sharpe(sr_variance, n_trials)
    return probabilistic_sharpe_ratio(returns, sr_benchmark=sr_star)
