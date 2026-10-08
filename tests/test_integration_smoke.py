"""Integração da Fase 0.1 — demonstra o GATE: run reproduzível bit-a-bit +
attempt log gravando/lendo + specs carregando.
"""
from pathlib import Path

import numpy as np

from research.attempt_registry import AttemptRegistry
from research.config import load_config
from research.reproducibility import capture_environment, fingerprint, set_seeds

ROOT = Path(__file__).resolve().parents[1]


def test_gate_reproducible_run_is_logged(tmp_path):
    cfg = load_config(ROOT / "config")

    def run(seed: int) -> str:
        set_seeds(seed)
        return fingerprint({"draw": np.random.rand(500).tolist(),
                            "cost_model": cfg.cost_model})

    fp1, fp2 = run(2026), run(2026)
    assert fp1 == fp2  # bit-a-bit

    reg = AttemptRegistry(tmp_path / "attempts.db")
    aid = reg.log(
        phase="0.1", name="foundation_smoke",
        config_hash=fingerprint(cfg.as_dict),
        params={"seed": 2026, "env": capture_environment()},
        result={"fingerprint": fp1},
    )
    assert reg.get(aid).result["fingerprint"] == fp1
    assert reg.count() == 1
