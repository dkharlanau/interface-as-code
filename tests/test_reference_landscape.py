import csv
from pathlib import Path

import yaml

from interface_as_code.diffing import semantic_diff
from interface_as_code.validator import schema_issues, semantic_issues


ROOT = Path(__file__).parents[1]
INVENTORY = ROOT / "examples" / "reference-landscape" / "inventory.csv"
CHANGE_DIR = ROOT / "examples" / "reference-landscape" / "changes"


def _rows():
    with INVENTORY.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_change(name: str):
    return yaml.safe_load((CHANGE_DIR / name).read_text(encoding="utf-8"))


def test_reference_landscape_has_30_unique_synthetic_interfaces():
    rows = _rows()
    ids = [row["interface_id"] for row in rows]

    assert len(rows) == 30
    assert len(ids) == len(set(ids))
    assert ids == [f"REF-{index:03d}" for index in range(1, 31)]


def test_reference_landscape_covers_core_integration_styles_and_sap_boundaries():
    rows = _rows()

    assert {row["protocol"] for row in rows} == {"IDoc", "REST", "Kafka", "CSV", "EDI"}
    systems = {row["source"] for row in rows} | {row["target"] for row in rows}
    assert {"SAP-MDG", "SAP-S4", "SAP-EWM", "SAP-TM"} <= systems
    assert {"CRM", "Commerce", "Warehouse", "Data-Lake", "Partner-Gateway", "MES", "TMS", "Finance"} <= systems


def test_reference_landscape_rows_have_operational_ownership_and_business_keys():
    for row in _rows():
        assert row["owner"].strip()
        assert row["support_route"].strip()
        assert row["business_key"].strip()


def test_controlled_change_is_schema_valid_but_operationally_weaker():
    before = _load_change("customer-replication-before.yaml")
    after = _load_change("customer-replication-after.yaml")

    assert schema_issues(before) == []
    assert schema_issues(after) == []
    assert semantic_issues(before) == []
    assert "at-least-once-idempotency-required" in {issue.code for issue in semantic_issues(after)}

    changes = {change.path: change.severity for change in semantic_diff(before, after)}
    assert changes["$.delivery.idempotency.required"] == "high-risk"
    assert changes["$.retry.max_attempts"] == "high-risk"
    assert changes["$.sla.recovery_target"] == "high-risk"
    assert changes["$.monitoring.signals"] == "informational"
