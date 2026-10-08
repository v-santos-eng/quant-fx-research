import numpy as np
import pytest

from research.validation import (
    deflated_sharpe_ratio,
    expected_max_sharpe,
    probabilistic_sharpe_ratio,
    sharpe_ratio,
    sharpe_std_error,
)


def test_sharpe_ratio_recovers_known():
    rng = np.random.default_rng(0)
    r = rng.normal(0.001, 0.01, 100_000)  # Sharpe por período ~0.1
    assert sharpe_ratio(r) == pytest.approx(0.1, abs=0.02)


def test_sharpe_annualization():
    rng = np.random.default_rng(1)
    r = rng.normal(0.0005, 0.01, 50_000)
    assert sharpe_ratio(r, periods_per_year=252) == pytest.approx(sharpe_ratio(r) * np.sqrt(252))


def test_sharpe_std_error_formula():
    assert sharpe_std_error(0.5, 100) == pytest.approx(np.sqrt((1 + 0.5 * 0.25) / 100))


def test_psr_high_for_clearly_positive():
    rng = np.random.default_rng(2)
    r = rng.normal(0.002, 0.005, 5_000)  # Sharpe forte e positivo
    assert probabilistic_sharpe_ratio(r, sr_benchmark=0.0) > 0.99


def test_psr_exactly_half_when_sample_sharpe_zero():
    rng = np.random.default_rng(3)
    r = rng.normal(0.0, 0.01, 20_000)
    r = r - r.mean()  # Sharpe REALIZADO da amostra = 0 -> PSR = Phi(0) = 0.5 exato
    assert probabilistic_sharpe_ratio(r, sr_benchmark=0.0) == pytest.approx(0.5, abs=1e-6)


def test_expected_max_sharpe_grows_with_trials():
    v = 0.25  # variância dos Sharpe dos ensaios
    assert expected_max_sharpe(v, 2) < expected_max_sharpe(v, 100) < expected_max_sharpe(v, 10_000)
    assert expected_max_sharpe(v, 1) == 0.0


def test_dsr_below_psr_under_multiple_trials():
    rng = np.random.default_rng(4)
    r = rng.normal(0.0015, 0.01, 5_000)
    psr = probabilistic_sharpe_ratio(r, sr_benchmark=0.0)
    dsr = deflated_sharpe_ratio(r, sr_variance=0.5, n_trials=1_000)
    assert dsr < psr  # deflacionar por muitos ensaios reduz a confiança
