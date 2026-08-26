from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
import yaml

@dataclass(frozen=True)
class DriftFinding:
    path: str
    declared: Any
    observed: Any
    source: str
    observed_at: str | None
    status: str
    message: str
    def to_dict(self): return asdict(self)


def _get(spec: Any, path: str) -> Any:
    if not path.startswith("$."):
        raise ValueError(f"Evidence path must start with $.: {path}")
    cur = spec
    for part in path[2:].split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def compare_evidence(spec: dict[str, Any], evidence: dict[str, Any], *, stale_after_days: int | None = None) -> list[DriftFinding]:
    findings: list[DriftFinding] = []
    for obs in evidence.get("observations", []):
        if not isinstance(obs, dict) or not obs.get("path"):
            continue
        path = str(obs["path"]); declared = _get(spec, path); observed = obs.get("value"); source = str(obs.get("source") or "unknown"); observed_at = obs.get("observed_at"); state = str(obs.get("status") or "observed")
        if state in {"unavailable", "stale"}:
            findings.append(DriftFinding(path, declared, observed, source, observed_at, state, f"Evidence is {state}; cannot conclude drift.")); continue
        if stale_after_days is not None and observed_at:
            try:
                when = datetime.fromisoformat(str(observed_at).replace("Z", "+00:00")); age=(datetime.now(timezone.utc)-when.astimezone(timezone.utc)).days
                if age > stale_after_days:
                    findings.append(DriftFinding(path, declared, observed, source, observed_at, "stale", f"Evidence is {age} days old; cannot conclude current drift.")); continue
            except ValueError:
                pass
        if declared != observed:
            findings.append(DriftFinding(path, declared, observed, source, observed_at, "drift", "Observed value differs from the declared specification."))
        else:
            findings.append(DriftFinding(path, declared, observed, source, observed_at, "match", "Observed evidence matches the declaration."))
    return findings


def load_evidence(path: str) -> dict[str, Any]:
    data = yaml.safe_load(open(path, encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("Evidence must be an object")
    return data
