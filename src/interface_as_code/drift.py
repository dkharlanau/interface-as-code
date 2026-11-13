from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
import math
import re
from typing import Any

import yaml

class _EvidenceLoader(yaml.SafeLoader):
    """Preserve timestamp spelling before strict validation (no normalization)."""


_EvidenceLoader.add_constructor(
    "tag:yaml.org,2002:timestamp", lambda loader, node: loader.construct_scalar(node)
)

_MISSING = object()
_COMPARABLE = {"match", "drift"}
_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)


def _json_value(value: Any, active: set[int] | None = None, depth: int = 0) -> bool:
    """Keep retained output finite, acyclic and deterministic, never default=str."""
    if depth > 100:
        return False
    if value is None or type(value) in (str, bool, int):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) not in (dict, list):
        return False
    active = set() if active is None else active
    if id(value) in active:
        return False
    active.add(id(value))
    try:
        if isinstance(value, dict):
            return all(type(key) is str and _json_value(item, active, depth + 1) for key, item in value.items())
        return all(_json_value(item, active, depth + 1) for item in value)
    finally:
        active.remove(id(value))


@dataclass(frozen=True)
class DriftFinding:
    path: str
    declared: Any
    observed: Any
    source: str
    observed_at: Any
    status: str
    message: str
    # Additive metadata: absence is not the same as an explicit null value.
    declared_present: bool = True
    observed_present: bool = True
    reason_code: str | None = None
    evaluated_at: str | None = None
    stale_after_days: int | None = None

    def to_dict(self):
        return asdict(self)


def _get(spec: Any, path: str) -> Any:
    if not isinstance(path, str) or not path.startswith("$.") or any(
        not part or "[" in part or "]" in part for part in path[2:].split(".")
    ):
        raise ValueError("Use a nonempty $.key.path (dictionary keys only).")
    cur = spec
    for part in path[2:].split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return _MISSING
    return cur


def _aware_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        when = value
    elif isinstance(value, str):
        if not _TIMESTAMP.fullmatch(value):
            raise ValueError("Use YYYY-MM-DDTHH:MM:SS[.ffffff] with Z or a valid ±HH:MM offset.")
        when = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError("Use an ISO 8601 datetime with Z or an explicit UTC offset.")
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError("Timestamp must include Z or an explicit UTC offset.")
    return when.astimezone(timezone.utc)


def _evaluation_time(value: datetime | str | None) -> datetime:
    return datetime.now(timezone.utc) if value is None else _aware_time(value)


def _same_value(left: Any, right: Any) -> bool:
    # Python otherwise treats True == 1, including inside containers.
    if isinstance(left, bool) != isinstance(right, bool):
        return False
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_same_value(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_same_value(a, b) for a, b in zip(left, right))
    return left == right


def compare_evidence(
    spec: dict[str, Any], evidence: dict[str, Any], *,
    stale_after_days: int | None = None, evaluated_at: datetime | str | None = None,
) -> list[DriftFinding]:
    """Compare offline observations; callers must validate the interface contract first.

    A supplied evaluation instant makes the output reproducible. With no freshness
    policy, timestamps remain descriptive: a match is not a claim of freshness.
    """
    if not isinstance(spec, dict) or not isinstance(evidence, dict):
        raise ValueError("Specification and evidence must be objects.")
    observations = evidence.get("observations")
    if not isinstance(observations, list):
        raise ValueError("Evidence must contain an observations list (possibly empty).")
    if stale_after_days is not None and (type(stale_after_days) is not int or stale_after_days < 0):
        raise ValueError("stale_after_days must be a nonnegative integer or None.")
    instant = _evaluation_time(evaluated_at)
    instant_text = instant.isoformat().replace("+00:00", "Z")
    findings: list[DriftFinding] = []
    for index, raw in enumerate(observations):
        obs = raw if isinstance(raw, dict) else {}
        path = obs.get("path")
        raw_source = obs.get("source", "unknown")
        source_valid = isinstance(raw_source, str) and bool(raw_source.strip())
        source = raw_source if source_valid else "unknown"
        observed_at = obs.get("observed_at")
        time_shape_valid = observed_at is None or isinstance(observed_at, (str, datetime))
        retained_time = observed_at.isoformat() if isinstance(observed_at, datetime) else observed_at if time_shape_valid else None
        observed = obs.get("value")
        value_valid = _json_value(observed)
        declared = _MISSING
        path_error = None
        try:
            declared = _get(spec, path)
        except ValueError as exc:
            path_error = str(exc)
        declared_valid = declared is _MISSING or _json_value(declared)
        finding = DriftFinding(
            path if isinstance(path, str) else f"observations[{index}]",
            None if declared is _MISSING or not declared_valid else declared, observed if value_valid else None, source, retained_time,
            "invalid", "", declared is not _MISSING, "value" in obs,
            evaluated_at=instant_text, stale_after_days=stale_after_days,
        )
        status, reason, message = "invalid", "invalid_observation", "Observation must be an object."
        if not isinstance(raw, dict):
            pass
        elif path_error:
            reason, message = "invalid_path", path_error
        elif not source_valid:
            reason, message = "invalid_source", "Source must be a nonempty string when supplied."
        elif not value_valid or not declared_valid:
            reason, message = "invalid_value", "Values must be finite, acyclic JSON-compatible data with string object keys (maximum depth 100)."
        elif not time_shape_valid and stale_after_days is None:
            reason, message = "invalid_time_type", "Timestamp metadata must be an ISO datetime string, YAML datetime or null."
        elif obs.get("status", "observed") not in ("observed", "unavailable", "stale"):
            reason, message = "unsupported_status", "Use observed, unavailable or stale status."
        elif obs.get("status") in ("unavailable", "stale"):
            status = obs["status"]
            reason, message = f"reported_{status}", f"Evidence is {status}; cannot conclude drift."
        elif declared is _MISSING:
            status, reason, message = "unknown", "declared_path_absent", "Declared path is absent; correct the path or the contract before comparing."
        elif "value" not in obs:
            status, reason, message = "unknown", "observed_value_absent", "Observation has no value; supply a value (explicit null is allowed)."
        else:
            status = "match" if _same_value(declared, observed) else "drift"
            reason = "values_equal" if status == "match" else "values_differ"
            message = "Observed evidence matches the declaration." if status == "match" else "Observed value differs from the declared specification."
            if stale_after_days is not None:
                try:
                    when = _aware_time(observed_at)
                except (ValueError, OverflowError) as exc:
                    status, reason = "unknown", "invalid_observed_at"
                    message = f"Freshness cannot be established: {exc}"
                else:
                    age_seconds = (instant - when).total_seconds()
                    if age_seconds < 0:
                        status, reason, message = "unknown", "future_observation", "Observation is later than the evaluation instant; check the clocks and evidence."
                    elif age_seconds > stale_after_days * 86400:
                        status, reason, message = "stale", "freshness_exceeded", "Evidence exceeds the freshness limit; collect a newer observation."
        findings.append(replace(finding, status=status, reason_code=reason, message=message))

    # No implicit last-write-wins or source precedence: a conflicting snapshot
    # needs a human decision, even when one observation matches the declaration.
    groups: dict[str, list[int]] = {}
    for index, finding in enumerate(findings):
        if finding.status in _COMPARABLE:
            groups.setdefault(finding.path, []).append(index)
    for indexes in groups.values():
        first = findings[indexes[0]].observed
        if any(not _same_value(first, findings[index].observed) for index in indexes[1:]):
            for index in indexes:
                findings[index] = replace(
                    findings[index], status="conflict", reason_code="conflicting_observations",
                    message="Comparable observations disagree on this path; resolve the evidence set or supply separate snapshots.",
                )
    return findings


def build_drift_report(spec: dict[str, Any], evidence: dict[str, Any], **options) -> dict[str, Any]:
    """Versioned retained output, including the evaluation policy for empty inputs."""
    instant = _evaluation_time(options.pop("evaluated_at", None))
    findings = compare_evidence(spec, evidence, evaluated_at=instant, **options)
    counts = dict(sorted(Counter(item.status for item in findings).items()))
    complete = bool(findings) and all(item.status in _COMPARABLE for item in findings)
    outcome = "inconclusive" if not complete else "drift" if counts.get("drift") else "match"
    return {
        "format": "interface-as-code-drift-report/1.0",
        "evaluated_at": instant.isoformat().replace("+00:00", "Z"),
        "freshness_policy": {"stale_after_days": options.get("stale_after_days"), "boundary": "age <= limit" if options.get("stale_after_days") is not None else None, "future_observations": "unknown" if options.get("stale_after_days") is not None else "not_checked"},
        "freshness_checked": options.get("stale_after_days") is not None,
        "outcome": outcome, "complete": complete, "counts": counts,
        "findings": [item.to_dict() for item in findings],
    }


def load_evidence(path: str) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        data = yaml.load(handle, Loader=_EvidenceLoader)
    if not isinstance(data, dict):
        raise ValueError("Evidence must be an object")
    return data
