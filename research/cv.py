"""Cross-validation para séries temporais (Fase 0.5) — Purged K-Fold com embargo
(López de Prado, cap. 7).

CV comum vaza em finanças: os rótulos se sobrepõem no tempo (um rótulo cobre um
horizonte de barras), então treino e teste compartilham informação. Solução:
  - PURGA: remove do treino toda observação cujo rótulo [início, fim] se sobrepõe
    ao intervalo de tempo do fold de teste.
  - EMBARGO: remove também as observações logo APÓS o teste (correlação serial).
"""
from __future__ import annotations

from itertools import combinations
from math import comb

import numpy as np
import pandas as pd


def make_label_spans(start_times, horizon: int) -> pd.Series:
    """t1: Series index=início do rótulo (tempo da obs), valor=fim do rótulo.

    O rótulo da obs i termina no início da barra i+horizon (trunca no fim da série).
    """
    idx = pd.DatetimeIndex(start_times)
    n = len(idx)
    pos = np.minimum(np.arange(n) + horizon, n - 1)
    return pd.Series(idx.values[pos], index=idx)


class PurgedKFold:
    """K-Fold com purga + embargo. `split(t1)` gera (train_idx, test_idx).

    t1: pd.Series ordenada por tempo (index=início do rótulo, valor=fim do rótulo).
    """

    def __init__(self, n_splits: int = 5, embargo_pct: float = 0.0):
        if n_splits < 2:
            raise ValueError("n_splits deve ser >= 2")
        if not 0.0 <= embargo_pct < 1.0:
            raise ValueError("embargo_pct em [0, 1)")
        self.n_splits = n_splits
        self.embargo_pct = embargo_pct

    def split(self, t1: pd.Series):
        n = len(t1)
        indices = np.arange(n)
        embargo = int(n * self.embargo_pct)
        starts = np.asarray(t1.index.values)
        ends = np.asarray(t1.values)
        for test_idx in np.array_split(indices, self.n_splits):
            t_start = starts[test_idx[0]]
            t_end = ends[test_idx].max()
            no_overlap = (ends < t_start) | (starts > t_end)   # purga por sobreposição
            mask = no_overlap.copy()
            mask[test_idx] = False                              # nunca treinar no teste
            if embargo > 0:                                     # embargo à direita do teste
                lo = test_idx[-1] + 1
                mask[lo:min(lo + embargo, n)] = False
            yield indices[mask], test_idx


class CombinatorialPurgedCV:
    """CPCV (López de Prado, cap. 12). Particiona em N grupos e testa em todas as
    C(N, k) combinações de k grupos, com purga+embargo. Gera múltiplos CAMINHOS de
    backtest (φ = k·C(N,k)/N), logo uma DISTRIBUIÇÃO de Sharpe em vez de um número.
    """

    def __init__(self, n_groups: int = 6, n_test_groups: int = 2, embargo_pct: float = 0.0):
        if not 2 <= n_test_groups < n_groups:
            raise ValueError("requer 2 <= n_test_groups < n_groups")
        if not 0.0 <= embargo_pct < 1.0:
            raise ValueError("embargo_pct em [0, 1)")
        self.n_groups = n_groups
        self.n_test_groups = n_test_groups
        self.embargo_pct = embargo_pct

    @property
    def n_splits(self) -> int:
        return comb(self.n_groups, self.n_test_groups)

    @property
    def n_paths(self) -> int:
        return self.n_test_groups * comb(self.n_groups, self.n_test_groups) // self.n_groups

    def split(self, t1: pd.Series):
        n = len(t1)
        indices = np.arange(n)
        embargo = int(n * self.embargo_pct)
        groups = np.array_split(indices, self.n_groups)
        starts = np.asarray(t1.index.values)
        ends = np.asarray(t1.values)
        for combo in combinations(range(self.n_groups), self.n_test_groups):
            test_idx = np.concatenate([groups[g] for g in combo])
            mask = np.ones(n, dtype=bool)
            mask[test_idx] = False
            for g in combo:                                     # purga+embargo por grupo de teste
                gi = groups[g]
                t_start, t_end = starts[gi[0]], ends[gi].max()
                mask &= (ends < t_start) | (starts > t_end)
                if embargo > 0:
                    lo = gi[-1] + 1
                    mask[lo:min(lo + embargo, n)] = False
            yield indices[mask], np.sort(test_idx)
