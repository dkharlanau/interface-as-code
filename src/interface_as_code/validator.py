from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any
import json

from jsonschema import Draft202012Validator

from .loader import load_yaml
from .resolver import ReferenceError, iter_references, resolve_reference

@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str
    code: str
    def __str__(self) -> str:
        return f"{self.path or '$'}: {self.message} [{self.code}]"

def _schema() -> dict[str, Any]:
    schema_file = resources.files("interface_as_code").joinpath("schemas/interface.schema.json")
    return json.loads(schema_file.read_text(encoding="utf-8"))

def _json_path(parts: list[Any]) -> str:
    return "$" if not parts else "$." + ".".join(str(part) for part in parts)

def schema_issues(spec: dict[str, Any]) -> list[ValidationIssue]:
    validator = Draft202012Validator(_schema())
    return [ValidationIssue(_json_path(list(e.path)), e.message, "schema") for e in sorted(validator.iter_errors(spec), key=lambda e: list(e.path))]

def semantic_issues(spec: dict[str, Any], base_dir: Path | None = None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    interface = spec.get("interface", {})
    contract = spec.get("contract", {})
    retry = spec.get("retry", {})
    mapping = spec.get("mapping", {})
    monitoring = spec.get("monitoring", {})
    reconciliation = spec.get("reconciliation", {})
    delivery = spec.get("delivery", {})
    if interface.get("mode") == "async" and not retry:
        issues.append(ValidationIssue("$.retry", "Asynchronous interfaces must define retry behavior.", "async-retry-required"))
    if contract.get("format") == "IDoc" and not contract.get("message_type"):
        issues.append(ValidationIssue("$.contract.message_type", "IDoc contracts must define message_type.", "idoc-message-type-required"))
    if retry.get("strategy") == "automatic" and (not isinstance(retry.get("max_attempts"), int) or retry.get("max_attempts", 0) < 1):
        issues.append(ValidationIssue("$.retry.max_attempts", "Automatic retry requires max_attempts >= 1.", "automatic-retry-attempts-required"))
    if delivery.get("guarantee") == "at-least-once" and not delivery.get("idempotency", {}).get("required"):
        issues.append(ValidationIssue("$.delivery.idempotency.required", "At-least-once delivery should require idempotent processing.", "at-least-once-idempotency-required"))
    if delivery.get("idempotency", {}).get("required") and not delivery.get("idempotency", {}).get("key"):
        issues.append(ValidationIssue("$.delivery.idempotency.key", "Required idempotency must define a key.", "idempotency-key-required"))
    if not monitoring.get("owner"):
        issues.append(ValidationIssue("$.monitoring.owner", "Every interface must have an operational owner.", "monitoring-owner-required"))
    if not reconciliation.get("key"):
        issues.append(ValidationIssue("$.reconciliation.key", "Every interface must define a reconciliation key.", "reconciliation-key-required"))
    consumers = interface.get("consumers", [])
    if consumers and any(c.get("system") == interface.get("source", {}).get("system") for c in consumers if isinstance(c, dict)):
        issues.append(ValidationIssue("$.interface.consumers", "A source system should not also be listed as a consumer in the same logical interface.", "source-consumer-cycle"))
    if base_dir and mapping.get("file") and not (base_dir / mapping["file"]).resolve().exists():
        issues.append(ValidationIssue("$.mapping.file", f"Referenced mapping file does not exist: {mapping['file']}", "mapping-file-missing"))
    schema_ref = contract.get("schema_ref")
    if base_dir and isinstance(schema_ref, str) and schema_ref.startswith(("./", "../")) and not (base_dir / schema_ref).resolve().exists():
        issues.append(ValidationIssue("$.contract.schema_ref", f"Referenced contract schema does not exist: {schema_ref}", "contract-schema-missing"))
    if base_dir:
        for index, test in enumerate(spec.get("tests", [])):
            fixture = test.get("fixture") if isinstance(test, dict) else None
            if fixture and not (base_dir / fixture).resolve().exists():
                issues.append(ValidationIssue(f"$.tests.{index}.fixture", f"Referenced test fixture does not exist: {fixture}", "test-fixture-missing"))
        for path, ref in iter_references(spec):
            try:
                resolve_reference(ref, base_dir)
            except ReferenceError as exc:
                issues.append(ValidationIssue(path, str(exc), "artifact-reference-invalid"))
    return issues

def validate_spec(path: str | Path) -> list[ValidationIssue]:
    spec_path = Path(path)
    spec = load_yaml(spec_path)
    issues = schema_issues(spec)
    if not issues:
        issues.extend(semantic_issues(spec, spec_path.parent))
    return issues

def discover_specs(path: str | Path) -> list[Path]:
    root = Path(path)
    if root.is_file():
        return [root]
    return sorted(root.rglob("interface.yaml"))
