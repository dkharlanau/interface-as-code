from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class SpecLoadError(ValueError):
    """Raised when a specification cannot be loaded."""


def load_yaml(path: str | Path) -> dict[str, Any]:
    spec_path = Path(path)
    try:
        raw = spec_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SpecLoadError(f"Cannot read {spec_path}: {exc}") from exc

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise SpecLoadError(f"Invalid YAML in {spec_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise SpecLoadError(f"{spec_path} must contain a YAML mapping at the root.")
    return data
