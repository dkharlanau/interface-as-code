#!/usr/bin/env python3
"""Validate Interface as Code conformance fixtures without importing the package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path):
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"fixture root must be an object: {path}")
    return value


def fixture_paths(root: Path, expectation: str) -> list[Path]:
    if expectation == "valid":
        # A valid scenario may carry referenced OpenAPI/AsyncAPI or other YAML files.
        # Only the Interface as Code root document is a spec conformance fixture.
        return sorted(root.rglob("interface.yaml"))
    # Invalid fixtures are deliberately standalone documents named by the failure case.
    return sorted(root.rglob("*.yaml"))


def run(version: str) -> dict:
    schema_path = ROOT / "spec" / f"v{version}" / "interface.schema.json"
    fixture_root = ROOT / "conformance" / f"v{version}"
    if not schema_path.exists():
        raise ValueError(f"unsupported conformance version: {version}")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    records = []
    failed = False
    for expectation in ("valid", "invalid"):
        for path in fixture_paths(fixture_root / expectation, expectation):
            errors = sorted(validator.iter_errors(load_yaml(path)), key=lambda item: list(item.path))
            observed = "invalid" if errors else "valid"
            passed = observed == expectation
            failed = failed or not passed
            records.append(
                {
                    "fixture": str(path.relative_to(ROOT)),
                    "expected": expectation,
                    "observed": observed,
                    "passed": passed,
                    "errors": [error.message for error in errors[:5]],
                }
            )

    if not records:
        raise ValueError(f"no conformance fixtures found for spec {version}")
    return {
        "spec_version": version,
        "schema": str(schema_path.relative_to(ROOT)),
        "fixtures": records,
        "passed": not failed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run public Interface as Code schema conformance fixtures")
    parser.add_argument("--spec-version", default="1.0")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = run(args.spec_version)
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"conformance error: {exc}")
        return 2
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for item in result["fixtures"]:
            status = "PASS" if item["passed"] else "FAIL"
            print(f"{status} {item['fixture']} expected={item['expected']} observed={item['observed']}")
        print(f"spec={result['spec_version']} fixtures={len(result['fixtures'])} passed={result['passed']}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
