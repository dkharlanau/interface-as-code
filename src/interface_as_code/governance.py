from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any
import yaml

from .policies import Finding

ALLOWED_OVERLAY_PREFIXES = ("interface.lifecycle", "interface.criticality", "route.external_ids", "route.middleware", "route.hops", "monitoring.", "sla.", "security.", "ownership.support", "retry.dead_letter")


def load_policy_pack(path: str | Path) -> dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("Policy pack must be a YAML object.")
    return data


def apply_policy_pack(findings: list[Finding], pack: dict[str, Any]) -> list[Finding]:
    rules = pack.get("rules", {}) if isinstance(pack.get("rules", {}), dict) else {}
    out: list[Finding] = []
    for finding in findings:
        cfg = rules.get(finding.code, {})
        if cfg is False or (isinstance(cfg, dict) and cfg.get("enabled") is False):
            continue
        if isinstance(cfg, dict) and cfg.get("severity"):
            finding = replace(finding, severity=str(cfg["severity"]))
        out.append(finding)
    return out


def _set_path(data: dict[str, Any], dotted: str, value: Any) -> None:
    if not any(dotted == p or dotted.startswith(p) for p in ALLOWED_OVERLAY_PREFIXES):
        raise ValueError(f"Overlay path is outside operational metadata boundary: {dotted}")
    current = data
    parts = dotted.split(".")
    for part in parts[:-1]:
        current = current.setdefault(part, {})
        if not isinstance(current, dict):
            raise ValueError(f"Cannot overlay through non-object path: {dotted}")
    current[parts[-1]] = value


def apply_overlay(spec: dict[str, Any], overlay: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    effective = deepcopy(spec)
    provenance: dict[str, str] = {}
    env = str(overlay.get("environment") or "overlay")
    sets = overlay.get("set", {})
    if not isinstance(sets, dict):
        raise ValueError("Overlay 'set' must be an object of dotted paths to values.")
    for dotted, value in sets.items():
        _set_path(effective, str(dotted), value)
        provenance[str(dotted)] = env
    return effective, provenance


def load_overlay(path: str | Path) -> dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("Overlay must be a YAML object.")
    return data
