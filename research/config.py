"""Carregamento e validação das specs YAML — fonte única de verdade (§4 da arquitetura).

As mesmas specs são consumidas por pesquisa (Python) e produção (MQL5), o que
mitiga o risco crítico R-01 (paridade Python<->MQL5).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

CONFIG_FILES = ("feature_spec", "cost_model", "risk_policy", "filters")


@dataclass(frozen=True)
class Config:
    feature_spec: dict
    cost_model: dict
    risk_policy: dict
    filters: dict

    @property
    def as_dict(self) -> dict:
        return {name: getattr(self, name) for name in CONFIG_FILES}


def load_config(config_dir: str | Path) -> Config:
    """Carrega as 4 specs de `config_dir`. Falha alto e cedo se algo faltar."""
    config_dir = Path(config_dir)
    data: dict = {}
    for name in CONFIG_FILES:
        path = config_dir / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Spec ausente: {path}")
        with open(path, encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
        if not isinstance(loaded, dict):
            raise ValueError(f"Spec '{name}' deve ser um mapeamento; veio {type(loaded).__name__}")
        data[name] = loaded
    return Config(**data)
