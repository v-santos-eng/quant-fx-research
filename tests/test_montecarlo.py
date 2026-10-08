import numpy as np
import pytest

from research.montecarlo import (
    block_bootstrap,
    max_drawdown,
    mc_distribution,
    param_sensitivity,
    time_underwater,
)


def test_max_drawdown_known():
    eq = [0, 5, 2, 8, 3, 10]  # picos 5 e 8; quedas 3 e 5 -> maxDD 5
    assert max_drawdown(eq) == pytest.approx(5.0)
    assert max_drawdown([1, 2, 3, 4]) == 0.0  # monotônico -> 0


def test_time_underwater_known():
    eq = [0, 1, 0.5, 0.4, 2, 1, 1, 3]  # submerso idx2-3 (2) e idx5-6 (2)
    assert time_underwater(eq) == 2
    assert time_underwater([1, 2, 3]) == 0


def test_block_bootstrap_shape_and_reproducible():
    pnl = np.arange(50.0)
    a = block_bootstrap(pnl, block_size=5, n_sims=100, rng=np.random.default_rng(0))
    b = block_bootstrap(pnl, block_size=5, n_sims=100, rng=np.random.default_rng(0))
    assert a.shape == (100, 50)
    assert np.array_equal(a, b)  # mesma seed -> idêntico


def test_block_bootstrap_constant_pnl():
    pnl = np.full(40, 2.0)                      # tudo igual -> toda curva é monotônica
    paths = block_bootstrap(pnl, 8, 50, rng=np.random.default_rng(1))
    assert np.allclose(paths[:, -1], 80.0)      # soma final = 40*2
    assert all(max_drawdown(p) == 0.0 for p in paths)  # sem drawdown


def test_mc_distribution_percentiles_ordered():
    rng = np.random.default_rng(2)
    pnl = rng.normal(0.1, 1.0, 500)
    d = mc_distribution(pnl, block_size=10, n_sims=500, rng=rng)
    dd = d["max_drawdown"]
    assert dd["p50"] <= dd["p95"] <= dd["p99"]  # percentis ordenados
    assert dd["p99"] >= 0.0


def test_param_sensitivity_smooth_metric():
    # métrica suave: platô -> perturbação muda pouco
    def metric(p):
        return -(p["x"] - 10.0) ** 2  # pico em x=10

    out = param_sensitivity(metric, {"x": 10.0}, pct=0.2)
    assert out["base"] == pytest.approx(0.0)
    pert = out["perturbations"]["x"]
    assert pert["low"] < out["base"] and pert["high"] < out["base"]  # cai dos dois lados (é um pico)
