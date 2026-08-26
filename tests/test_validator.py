from pathlib import Path

import yaml

from interface_as_code.validator import semantic_issues, validate_spec


ROOT = Path(__file__).parents[1]


def test_sap_example_is_valid():
    path = ROOT / "examples" / "sap-mdg-to-s4-customer" / "interface.yaml"
    assert validate_spec(path) == []


def test_rest_example_is_valid():
    path = ROOT / "examples" / "rest-order-api" / "interface.yaml"
    assert validate_spec(path) == []


def test_at_least_once_requires_idempotency():
    spec = {
        "delivery": {
            "guarantee": "at-least-once",
            "idempotency": {"required": False},
        },
        "monitoring": {"owner": "Ops"},
        "reconciliation": {"key": "id"},
    }
    codes = {issue.code for issue in semantic_issues(spec)}
    assert "at-least-once-idempotency-required" in codes


def test_idoc_requires_message_type():
    spec = {
        "contract": {"format": "IDoc"},
        "monitoring": {"owner": "Ops"},
        "reconciliation": {"key": "id"},
    }
    codes = {issue.code for issue in semantic_issues(spec)}
    assert "idoc-message-type-required" in codes


def test_missing_mapping_reference_is_reported(tmp_path):
    spec = {
        "mapping": {"file": "missing.yaml"},
        "monitoring": {"owner": "Ops"},
        "reconciliation": {"key": "id"},
    }
    codes = {issue.code for issue in semantic_issues(spec, tmp_path)}
    assert "mapping-file-missing" in codes


def test_missing_local_contract_schema_is_reported(tmp_path):
    spec = {
        "contract": {"format": "REST", "schema_ref": "./missing.yaml"},
        "monitoring": {"owner": "Ops"},
        "reconciliation": {"key": "id"},
    }
    codes = {issue.code for issue in semantic_issues(spec, tmp_path)}
    assert "contract-schema-missing" in codes


def test_missing_test_fixture_is_reported(tmp_path):
    spec = {
        "monitoring": {"owner": "Ops"},
        "reconciliation": {"key": "id"},
        "tests": [{"id": "x", "description": "x", "fixture": "missing.yaml"}],
    }
    codes = {issue.code for issue in semantic_issues(spec, tmp_path)}
    assert "test-fixture-missing" in codes
