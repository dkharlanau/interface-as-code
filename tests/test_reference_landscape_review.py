from __future__ import annotations

import json
from pathlib import Path

from scripts.build_reference_landscape_review import build_review


def test_reference_landscape_review_set(tmp_path: Path):
    output = tmp_path / "reference-review"
    review_set = build_review(output)

    assert review_set["format"] == "interface-as-code-reference-review/0.1"
    assert review_set["status"] == "synthetic-implementation-proof"
    assert all(review_set["assertions"].values())

    summary = review_set["summary"]
    assert summary["inventory_rows"] == 30
    assert summary["import"] == {"generated": 30, "gaps": 0}
    assert summary["readiness"]["valid"] == 30
    assert summary["readiness"]["invalid"] == 0
    assert summary["readiness"]["findings_by_severity"].get("error", 0) == 0
    assert summary["readiness"]["interfaces_with_warnings"] > 0
    assert summary["catalog"]["total"] == 30
    assert summary["catalog"]["invalid"] == 0
    assert set(summary["representative"]["protocols"]) == {"IDoc", "REST", "Kafka", "CSV", "EDI"}
    assert summary["semantic_change"]["severity"] == "breaking"
    assert summary["drift"] == {
        "interface_id": "REF-003",
        "match": 1,
        "drift": 1,
        "scope": "Synthetic observed evidence used only to prove drift classification; not runtime evidence from a real landscape.",
    }

    boundary = review_set["validation_boundary"]
    assert boundary == {
        "external_practitioner_validation": False,
        "production_runtime_evidence": False,
        "customer_specific_fit": False,
        "production_readiness": False,
    }

    expected = [
        "review-set.json",
        "summary.json",
        "readiness.json",
        "review.md",
        "catalog/index.json",
        "catalog/index.html",
        "catalog/topology.mmd",
        "semantic-change/before.interface.yaml",
        "semantic-change/after.interface.yaml",
        "semantic-change/diff.json",
        "drift/evidence.yaml",
        "drift/findings.json",
        "representative/ref-001/controls.yaml",
        "representative/ref-001/observability.yaml",
        "representative/ref-001/test-plan.yaml",
        "representative/ref-001/backstage.yaml",
        "representative/ref-001/leanix.yaml",
        "representative/ref-001/sap-summary.yaml",
        "representative/ref-005/backstage.yaml",
        "representative/ref-005/leanix.yaml",
    ]
    for relative in expected:
        assert (output / relative).exists(), relative

    data = json.loads((output / "review-set.json").read_text(encoding="utf-8"))
    assert data["assertions"] == review_set["assertions"]

    review = (output / "review.md").read_text(encoding="utf-8")
    assert "Readiness truth" in review
    assert "Change and drift proof" in review
    assert "external practitioner validation" in review.lower()
