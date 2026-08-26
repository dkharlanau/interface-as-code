from __future__ import annotations

from typing import Any
import yaml


def generate_test_plan(spec: dict[str, Any]) -> dict[str, Any]:
    i, c = spec["interface"], spec["contract"]
    d, r, rec = spec.get("delivery", {}), spec.get("retry", {}), spec.get("reconciliation", {})
    cases: list[dict[str, Any]] = [
        {"id":"contract-valid","purpose":"Valid payload/message satisfies the referenced contract.","expected":"accepted"},
        {"id":"contract-invalid","purpose":"Invalid payload/message is rejected observably.","expected":"controlled rejection"},
        {"id":"happy-path","purpose":"Business transaction reaches the intended consumer.","expected":"processed"},
    ]
    if d.get("idempotency", {}).get("required"):
        cases.append({"id":"duplicate-delivery","purpose":f"Replay the same `{d['idempotency'].get('key')}` twice.","expected":"no duplicate business state"})
    if r.get("strategy") == "automatic":
        cases.append({"id":"retry-exhaustion","purpose":"Force repeated transient failure until retry limit.","expected":f"stops after {r.get('max_attempts','configured')} attempts"})
    if r.get("dead_letter"):
        cases.append({"id":"dead-letter","purpose":"Force non-recoverable failure.","expected":f"retained in {r['dead_letter']}"})
    if i.get("mode") in {"async","batch"}:
        cases.append({"id":"safe-replay","purpose":"Correct failure and replay through declared procedure.","expected":"converged without duplicate state"})
    if rec.get("key"):
        cases.append({"id":"reconciliation","purpose":f"Compare source and target using `{rec['key']}`.","expected":rec.get("comparison") or "source and target converge"})
    if spec.get("security", {}).get("external_exposure"):
        cases.append({"id":"unauthorized-request","purpose":"Call/exchange without valid authentication.","expected":"rejected without sensitive leakage"})
    pact_refs = []
    for test in spec.get("tests", []):
        ref = test.get("evidence_ref", {}) if isinstance(test, dict) else {}
        if ref.get("kind") == "pact":
            pact_refs.append(ref.get("uri"))
    return {"interface_id":i["id"],"contract_format":c["format"],"cases":cases,"pact_sources":pact_refs,"evidence_expected":True}


def render(spec: dict[str, Any], format_name="markdown") -> str:
    plan = generate_test_plan(spec)
    if format_name == "yaml":
        return yaml.safe_dump(plan, sort_keys=False)
    lines=[f"# Test plan — {plan['interface_id']}","",f"Contract: **{plan['contract_format']}**","","| ID | Purpose | Expected |","| --- | --- | --- |"]
    for case in plan["cases"]:
        lines.append(f"| `{case['id']}` | {case['purpose']} | {case['expected']} |")
    if plan["pact_sources"]:
        lines += ["","Pact remains the consumer/provider contract-test source of truth:",*[f"- `{x}`" for x in plan["pact_sources"]]]
    return "\n".join(lines)+"\n"
