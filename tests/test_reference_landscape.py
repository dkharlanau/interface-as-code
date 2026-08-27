import csv
from pathlib import Path


ROOT = Path(__file__).parents[1]
INVENTORY = ROOT / "examples" / "reference-landscape" / "inventory.csv"


def _rows():
    with INVENTORY.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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
