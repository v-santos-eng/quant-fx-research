"""Reprodutibilidade (RNF-01): seeds determinísticos, captura de ambiente e
fingerprint estável de qualquer objeto JSON-serializável.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import random
from importlib import metadata

DEFAULT_PACKAGES = ("numpy", "PyYAML", "pytest")


def set_seeds(seed: int) -> None:
    """Fixa todas as fontes de aleatoriedade usadas no projeto."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        pass  # ponytail: numpy é opcional aqui; entra como dep na Fase 0.1


def capture_environment(packages: tuple[str, ...] = DEFAULT_PACKAGES) -> dict:
    """Snapshot do ambiente para o attempt log — permite reexecutar um resultado."""
    versions: dict[str, str | None] = {}
    for pkg in packages:
        try:
            versions[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            versions[pkg] = None
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": versions,
    }


def fingerprint(obj) -> str:
    """SHA-256 estável de `obj` (chaves ordenadas). Base do run reproduzível bit-a-bit."""
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
