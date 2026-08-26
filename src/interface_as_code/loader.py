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

def dump_yaml(data: dict[str, Any], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
