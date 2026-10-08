from pathlib import Path

from research.config import CONFIG_FILES, load_config

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


def test_loads_all_specs():
    cfg = load_config(CONFIG_DIR)
    for name in CONFIG_FILES:
        assert isinstance(getattr(cfg, name), dict), name


def test_cost_model_has_three_layers():
    cfg = load_config(CONFIG_DIR)
    for layer in ("spread", "slippage", "swap"):
        assert layer in cfg.cost_model


def test_missing_spec_raises(tmp_path):
    import pytest

    with pytest.raises(FileNotFoundError):
        load_config(tmp_path)
