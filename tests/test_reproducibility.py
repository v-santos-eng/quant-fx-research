import numpy as np

from research.reproducibility import capture_environment, fingerprint, set_seeds


def _run(seed: int) -> str:
    set_seeds(seed)
    return fingerprint(np.random.rand(1000).tolist())


def test_same_seed_is_bit_for_bit():
    assert _run(42) == _run(42)


def test_different_seed_differs():
    assert _run(42) != _run(7)


def test_fingerprint_is_order_independent():
    assert fingerprint({"a": 1, "b": 2}) == fingerprint({"b": 2, "a": 1})


def test_environment_captured():
    env = capture_environment()
    assert env["python"].startswith("3.")
    assert "numpy" in env["packages"]
