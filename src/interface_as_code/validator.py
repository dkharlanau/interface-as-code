from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .loader import load_yaml


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str
    code: str

    def __str__(self) -> str:
        location = self.path or "$"
        return f"{location}: {self.message} [{self.code}]"


def _schema() -> dict[str, Any]:
    schema_file = resources.files("interface_as_code").joinpath(
        "schemas/interface.schema.json"
    )
    import json
    return json.loads(schema_file.read_text(encoding="utf-8"))


def _json_path(parts: list[Any]) -> str:
    if not parts:
        return "$"
    return "$." + ".".join(str(part) for part in parts)


def schema_issues(spec: dict[str, Any]) -> list[ValidationIssue]:
    validator = Draft202012Validator(_schema())
    issues = []
    for error in sorted(validator.iter_errors(spec), key=lambda e: list(e.path)):
        issues.append(
            ValidationIssue(
                path=_json_path(list(error.path)),
                message=error.message,
                code="schema",
            )
        )
    return issues


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
        issues.append(
            ValidationIssue(
                "$.retry",
                "Asynchronous interfaces must define retry behavior.",
                "async-retry-required",
            )
        )

    if contract.get("format") == "IDoc" and not contract.get("message_type"):
        issues.append(
            ValidationIssue(
                "$.contract.message_type",
                "IDoc contracts must define message_type.",
                "idoc-message-type-required",
            )
        )

    if retry.get("strategy") == "automatic":
        attempts = retry.get("max_attempts")
        if not isinstance(attempts, int) or attempts < 1:
            issues.append(
                ValidationIssue(
                    "$.retry.max_attempts",
                    "Automatic retry requires max_attempts >= 1.",
                    "automatic-retry-attempts-required",
                )
            )

    if delivery.get("guarantee") == "at-least-once":
        idempotency = delivery.get("idempotency", {})
        if not idempotency.get("required"):
            issues.append(
                ValidationIssue(
                    "$.delivery.idempotency.required",
                    "At-least-once delivery should require idempotent processing.",
                    "at-least-once-idempotency-required",
                )
            )

    if not monitoring.get("owner"):
        issues.append(
            ValidationIssue(
                "$.monitoring.owner",
                "Every interface must have an operational owner.",
                "monitoring-owner-required",
            )
        )

    if not reconciliation.get("key"):
        issues.append(
            ValidationIssue(
                "$.reconciliation.key",
                "Every interface must define a reconciliation key.",
                "reconciliation-key-required",
            )
        )

    if base_dir and mapping.get("file"):
        mapping_file = (base_dir / mapping["file"]).resolve()
        if not mapping_file.exists():
            issues.append(
                ValidationIssue(
                    "$.mapping.file",
                    f"Referenced mapping file does not exist: {mapping['file']}",
                    "mapping-file-missing",
                )
            )

    schema_ref = contract.get("schema_ref")
    if base_dir and isinstance(schema_ref, str) and schema_ref.startswith(("./", "../")):
        schema_file = (base_dir / schema_ref).resolve()
        if not schema_file.exists():
            issues.append(
                ValidationIssue(
                    "$.contract.schema_ref",
                    f"Referenced contract schema does not exist: {schema_ref}",
                    "contract-schema-missing",
                )
            )

    if base_dir:
        for index, test in enumerate(spec.get("tests", [])):
            fixture = test.get("fixture")
            if fixture:
                fixture_file = (base_dir / fixture).resolve()
                if not fixture_file.exists():
                    issues.append(
                        ValidationIssue(
                            f"$.tests.{index}.fixture",
                            f"Referenced test fixture does not exist: {fixture}",
                            "test-fixture-missing",
                        )
                    )

    return issues


def validate_spec(path: str | Path) -> list[ValidationIssue]:
    spec_path = Path(path)
    spec = load_yaml(spec_path)
    issues = schema_issues(spec)
    if not issues:
        issues.extend(semantic_issues(spec, spec_path.parent))
    return issues
