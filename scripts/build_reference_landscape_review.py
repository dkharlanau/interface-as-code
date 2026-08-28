from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from interface_as_code.adapters import render_adapter
from interface_as_code.catalog import build_catalog
from interface_as_code.controls import render_controls
from interface_as_code.diffing import semantic_diff
from interface_as_code.drift import compare_evidence
from interface_as_code.importer import import_csv
from interface_as_code.loader import dump_yaml, load_yaml
from interface_as_code.observability import render as render_observability
from interface_as_code.policies import check_spec
from interface_as_code.sap import render_sap_summary
from interface_as_code.testplan import render as render_test_plan
from interface_as_code.validator import discover_specs, validate_spec

INVENTORY = ROOT / "examples" / "reference-landscape" / "inventory.csv"
DEFAULT_OUTPUT = ROOT / "build" / "reference-landscape-review"
REPRESENTATIVE_IDS = ["REF-001", "REF-002", "REF-003", "REF-004", "REF-005"]
EXPECTED_PROTOCOLS = {"IDoc", "REST", "Kafka", "CSV", "EDI"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _read_inventory_count() -> int:
    with INVENTORY.open(encoding="utf-8") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def _materialize_landscape(output: Path) -> tuple[Path, dict[str, Any], list[Path]]:
    generated = output / "generated"
    report = import_csv(INVENTORY, generated)
    specs = discover_specs(generated)
    if len(specs) != _read_inventory_count():
        raise AssertionError(f"expected {_read_inventory_count()} generated specs, got {len(specs)}")
    if report["gaps"]:
        raise AssertionError(f"reference inventory import unexpectedly produced gaps: {report['gaps']}")
    return generated, report, specs


def _validate_and_score(specs: list[Path]) -> dict[str, Any]:
    invalid: list[dict[str, Any]] = []
    severity = Counter()
    codes = Counter()
    interfaces_with_findings = 0
    interfaces_with_warnings = 0
    lifecycle = Counter()
    protocols = Counter()

    for path in specs:
        issues = validate_spec(path)
        if issues:
            invalid.append({"path": str(path), "issues": [str(issue) for issue in issues]})
            continue
        spec = load_yaml(path)
        findings = check_spec(spec)
        lifecycle[str(spec["interface"].get("lifecycle") or "unknown")] += 1
        protocols[str(spec["contract"]["format"])] += 1
        if findings:
            interfaces_with_findings += 1
        if any(item.severity == "warning" for item in findings):
            interfaces_with_warnings += 1
        for item in findings:
            severity[item.severity] += 1
            codes[item.code] += 1

    if invalid:
        raise AssertionError(f"reference landscape contains invalid interface specs: {invalid}")
    if severity.get("error", 0) != 0:
        raise AssertionError("reference landscape readiness unexpectedly contains error-level findings")
    if set(protocols) != EXPECTED_PROTOCOLS:
        raise AssertionError(f"protocol coverage drifted: {sorted(protocols)}")
    if interfaces_with_warnings == 0:
        raise AssertionError("reference landscape should retain visible operational readiness debt")

    return {
        "valid": len(specs),
        "invalid": 0,
        "interfaces_with_findings": interfaces_with_findings,
        "interfaces_with_warnings": interfaces_with_warnings,
        "findings_by_severity": dict(sorted(severity.items())),
        "top_findings": [
            {"code": code, "count": count}
            for code, count in codes.most_common(12)
        ],
        "lifecycle": dict(sorted(lifecycle.items())),
        "protocols": dict(sorted(protocols.items())),
        "interpretation": "All 30 synthetic contracts are structurally valid, but readiness warnings remain intentionally visible because imported inventory is not treated as production evidence.",
    }


def _spec_by_id(specs: list[Path]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for path in specs:
        spec = load_yaml(path)
        result[str(spec["interface"]["id"])] = path
    return result


def _generate_representative_outputs(specs: list[Path], output: Path) -> dict[str, Any]:
    by_id = _spec_by_id(specs)
    representative_root = output / "representative"
    summary: list[dict[str, Any]] = []
    protocols: set[str] = set()

    for interface_id in REPRESENTATIVE_IDS:
        path = by_id.get(interface_id)
        if path is None:
            raise AssertionError(f"representative interface is missing: {interface_id}")
        spec = load_yaml(path)
        protocol = str(spec["contract"]["format"])
        protocols.add(protocol)
        item_dir = representative_root / interface_id.lower()
        item_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, item_dir / "interface.yaml")
        _write_text(item_dir / "controls.yaml", render_controls(spec, "yaml"))
        _write_text(item_dir / "observability.yaml", render_observability(spec, "yaml"))
        _write_text(item_dir / "test-plan.yaml", render_test_plan(spec, "yaml"))
        _write_text(item_dir / "backstage.yaml", render_adapter(spec, "backstage"))
        _write_text(item_dir / "leanix.yaml", render_adapter(spec, "leanix"))
        systems = [spec["interface"]["source"]["system"]]
        systems.extend(target["system"] for target in (spec["interface"].get("consumers") or [spec["interface"]["target"]]))
        sap_relevant = any(str(system).startswith("SAP-") for system in systems)
        if sap_relevant:
            _write_text(item_dir / "sap-summary.yaml", render_sap_summary(spec, "yaml"))
        summary.append({
            "id": interface_id,
            "protocol": protocol,
            "source": spec["interface"]["source"]["system"],
            "target": spec["interface"]["target"]["system"],
            "criticality": spec["interface"].get("criticality"),
            "sap_relevant": sap_relevant,
            "outputs": [path.name for path in sorted(item_dir.iterdir())],
        })

    if protocols != EXPECTED_PROTOCOLS:
        raise AssertionError(f"representative set does not cover all expected protocols: {sorted(protocols)}")
    return {"interfaces": summary, "protocols": sorted(protocols)}


def _semantic_change_proof(specs: list[Path], output: Path) -> dict[str, Any]:
    by_id = _spec_by_id(specs)
    source = by_id["REF-006"]
    old = load_yaml(source)
    new = copy.deepcopy(old)
    old_target = new["interface"]["target"]["system"]
    new["interface"]["target"]["system"] = f"{old_target}-V2"

    change_root = output / "semantic-change"
    dump_yaml(old, change_root / "before.interface.yaml")
    dump_yaml(new, change_root / "after.interface.yaml")
    changes = [change.to_dict() for change in semantic_diff(old, new)]
    _write_json(change_root / "diff.json", changes)

    target_change = next((item for item in changes if item["path"] == "$.interface.target.system"), None)
    if target_change is None or target_change["severity"] != "breaking":
        raise AssertionError(f"target topology change was not classified as breaking: {changes}")
    return {
        "interface_id": "REF-006",
        "changed_path": target_change["path"],
        "old": target_change["old"],
        "new": target_change["new"],
        "severity": target_change["severity"],
        "reason": target_change["reason"],
    }


def _drift_proof(specs: list[Path], output: Path) -> dict[str, Any]:
    by_id = _spec_by_id(specs)
    spec = load_yaml(by_id["REF-003"])
    evidence = {
        "format": "interface-observations/0.1",
        "interface_id": "REF-003",
        "synthetic": True,
        "observations": [
            {
                "path": "$.contract.format",
                "value": spec["contract"]["format"],
                "source": "synthetic-runtime-inventory",
                "observed_at": "2026-08-28T12:00:00Z",
            },
            {
                "path": "$.reconciliation.key",
                "value": "BusinessPartner",
                "source": "synthetic-runtime-inventory",
                "observed_at": "2026-08-28T12:00:00Z",
            },
        ],
    }
    drift_root = output / "drift"
    _write_text(drift_root / "evidence.yaml", yaml.safe_dump(evidence, sort_keys=False))
    findings = [item.to_dict() for item in compare_evidence(spec, evidence)]
    _write_json(drift_root / "findings.json", findings)
    states = Counter(item["status"] for item in findings)
    if states.get("match") != 1 or states.get("drift") != 1:
        raise AssertionError(f"drift fixture should prove one match and one drift: {findings}")
    return {
        "interface_id": "REF-003",
        "match": states.get("match", 0),
        "drift": states.get("drift", 0),
        "scope": "Synthetic observed evidence used only to prove drift classification; not runtime evidence from a real landscape.",
    }


def _render_review(summary: dict[str, Any]) -> str:
    readiness = summary["readiness"]
    catalog = summary["catalog"]
    change = summary["semantic_change"]
    drift = summary["drift"]
    return "\n".join([
        "# Interface as Code — Reference Landscape Review",
        "",
        "Status: **synthetic implementation proof**, not external practitioner validation.",
        "",
        "## Landscape",
        "",
        f"- Imported inventory: **{summary['inventory_rows']} interfaces**.",
        f"- Structural validation: **{readiness['valid']}/{summary['inventory_rows']} valid**.",
        f"- Catalog: **{catalog['total']} interfaces**, **{catalog['systems']} systems**, protocols `{', '.join(sorted(catalog['protocols']))}`.",
        f"- Representative operational projections: **{len(summary['representative']['interfaces'])} interfaces / {len(summary['representative']['protocols'])} protocol styles**.",
        "",
        "## Readiness truth",
        "",
        f"The imported landscape has **{readiness['findings_by_severity'].get('error', 0)} error-level findings** and **{readiness['findings_by_severity'].get('warning', 0)} warnings**. Warnings are retained deliberately: an imported inventory is not silently promoted to production-ready interface contracts.",
        "",
        "Highest-frequency gaps are stored in `readiness.json`; generated interface contracts remain lifecycle `proposed` until owners fill replay, reconciliation, SLA, testing and other operational details.",
        "",
        "## Change and drift proof",
        "",
        f"- Semantic change fixture: `{change['changed_path']}` on `{change['interface_id']}` is classified **{change['severity']}**.",
        f"- Drift fixture: `{drift['interface_id']}` contains **{drift['match']} match** and **{drift['drift']} drift** observation.",
        "",
        "## Generated operational projections",
        "",
        "For one representative contract of each core integration style, the bundle retains:",
        "",
        "- operational controls / reconciliation model;",
        "- observability requirements;",
        "- generated test plan;",
        "- Backstage resource projection;",
        "- LeanIX catalog projection;",
        "- SAP summary where a SAP boundary is present.",
        "",
        "## What this proves — and what it does not",
        "",
        "It proves that one 30-interface heterogeneous inventory can be imported, validated, scored for readiness, cataloged, projected into operational/enterprise architecture views, semantically diffed and checked for runtime drift with one deterministic toolchain.",
        "",
        "It does **not** prove production fitness, customer-specific correctness, runtime connector coverage or independent practitioner value. The next maturity gate is external review/use of the reference landscape rather than adding more synthetic rows.",
        "",
    ])


def build_review(output: Path, *, force: bool = False) -> dict[str, Any]:
    output = output.resolve()
    if output.exists() and any(output.iterdir()):
        if not force:
            raise ValueError(f"output directory is not empty: {output}; use --force")
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    shutil.copy2(INVENTORY, output / "inventory.csv")
    generated, import_report, specs = _materialize_landscape(output)
    readiness = _validate_and_score(specs)
    _write_json(output / "readiness.json", readiness)

    catalog = build_catalog(generated, output / "catalog")
    if catalog["summary"]["total"] != 30 or catalog["summary"]["invalid"] != 0:
        raise AssertionError(f"catalog did not contain 30 valid interfaces: {catalog['summary']}")

    representative = _generate_representative_outputs(specs, output)
    semantic_change = _semantic_change_proof(specs, output)
    drift = _drift_proof(specs, output)

    summary = {
        "inventory_rows": _read_inventory_count(),
        "import": {
            "generated": len(import_report["generated"]),
            "gaps": len(import_report["gaps"]),
        },
        "readiness": readiness,
        "catalog": catalog["summary"],
        "representative": representative,
        "semantic_change": semantic_change,
        "drift": drift,
    }
    _write_json(output / "summary.json", summary)
    _write_text(output / "review.md", _render_review(summary))

    manifest: dict[str, dict[str, Any]] = {}
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "review-set.json":
            manifest[str(path.relative_to(output))] = {
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }

    review_set = {
        "format": "interface-as-code-reference-review/0.1",
        "status": "synthetic-implementation-proof",
        "summary": summary,
        "assertions": {
            "inventory_has_30_interfaces": summary["inventory_rows"] == 30,
            "import_has_no_source_gaps": summary["import"]["gaps"] == 0,
            "all_interfaces_structurally_valid": readiness["valid"] == 30 and readiness["invalid"] == 0,
            "readiness_errors_are_zero": readiness["findings_by_severity"].get("error", 0) == 0,
            "readiness_debt_remains_visible": readiness["interfaces_with_warnings"] > 0,
            "catalog_covers_all_interfaces": catalog["summary"]["total"] == 30,
            "representative_set_covers_five_protocols": set(representative["protocols"]) == EXPECTED_PROTOCOLS,
            "breaking_topology_change_detected": semantic_change["severity"] == "breaking",
            "drift_fixture_detects_match_and_drift": drift["match"] == 1 and drift["drift"] == 1,
        },
        "validation_boundary": {
            "external_practitioner_validation": False,
            "production_runtime_evidence": False,
            "customer_specific_fit": False,
            "production_readiness": False,
        },
        "artifacts": manifest,
    }
    if not all(review_set["assertions"].values()):
        raise AssertionError(f"reference review assertions failed: {review_set['assertions']}")
    _write_json(output / "review-set.json", review_set)
    print(json.dumps({
        "status": review_set["status"],
        "interfaces": summary["inventory_rows"],
        "assertions": review_set["assertions"],
        "output": str(output),
    }, indent=2))
    return review_set


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the 30-interface synthetic reference landscape review set.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    build_review(args.output, force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
