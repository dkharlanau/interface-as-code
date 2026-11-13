"""A declaration-based support brief. It never executes a test or grants approval."""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
from typing import Any

import yaml

from .controls import control_model
from .loader import SpecLoadError
from .policies import _missing, check_spec
from .testplan import generate_test_plan
from .validator import schema_issues, semantic_issues

QUESTIONS = {
    "owner.missing": "Which team accepts operational responsibility for failures?",
    "owner.technical-missing": "Who reviews technical changes to this interface?",
    "owner.business-missing": "Who decides the business impact of a failed or delayed transaction?",
    "owner.support-missing": "Who provides support and escalation for this critical interface?",
    "support.route-missing": "Where should support open or route an incident?",
    "observability.business-key-missing": "Which business key connects a message to its source and target transaction?",
    "recoverability.replay-guidance-missing": "What correction, duplicate-state check and authorization are required before replay?",
    "reconciliation.comparison-missing": "Which source and target populations or values should be compared?",
    "reconciliation.key-missing": "Which stable business key joins the source and target reconciliation?",
    "delivery.idempotency-key-missing": "Which stable key prevents duplicate business state?",
    "delivery.idempotency-required": "How will repeated delivery avoid duplicate business state?",
    "recoverability.retry-missing": "Who owns recovery, and what retry behavior is intended?",
    "recoverability.retry-unbounded": "How many automatic retries are allowed before escalation?",
    "recoverability.dead-letter-missing": "Where are failed messages retained for investigation?",
    "observability.signals-missing": "Which signals reveal technical and business processing failures?",
    "observability.critical-signal-coverage": "Which additional signals expose latency, backlog or business failure?",
    "sla.missing": "What latency and recovery expectations has the business accepted?",
    "sla.recovery-target-missing": "What is the maximum acceptable recovery time?",
    "tests.missing": "Which happy-path, failure and replay scenarios must be checked?",
    "tests.active-without-tests": "What test intent supports treating this active interface as ready?",
    "evidence.missing": "Where is the reviewed test or runtime evidence for this exact contract?",
    "security.auth-missing": "Which authentication mechanism protects the exposed interface?",
    "security.encryption-required": "How is personal data protected in transport?",
    "security.classification-missing": "How is the transported data classified?",
    "delivery.best-effort-critical": "What delivery model or reviewed exception justifies this critical interface?",
    "retry.sync-manual": "Does the caller or an operator own retries for this synchronous API?",
    "mapping.missing": "Where is mapping behavior defined, or where is identity mapping explicitly declared?",
    "batch.schedule-missing": "What batch cadence should support expect?",
}
PRIORITY = (
    "owner.missing", "support.route-missing", "owner.support-missing",
    "observability.business-key-missing", "recoverability.replay-guidance-missing",
    "reconciliation.comparison-missing", "reconciliation.key-missing",
)
CONTACT_PATHS = (
    ("operational", "monitoring", "owner"),
    ("support", "ownership", "support"),
    ("technical", "ownership", "technical"),
    ("business", "ownership", "business"),
)


def _load_contract(path: str | Path) -> tuple[Path, bytes, dict[str, Any]]:
    """Load once and validate exactly the declaration whose bytes are retained."""
    source = Path(path)
    try:
        raw = source.read_bytes()
        spec = yaml.safe_load(raw.decode("utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise SpecLoadError(f"Cannot load handover contract {source}: {exc}") from exc
    if not isinstance(spec, dict):
        raise SpecLoadError("Handover contract must contain a YAML mapping.")
    issues = schema_issues(spec)
    if not issues:
        issues = semantic_issues(spec, source.parent)
    if issues:
        raise SpecLoadError("Invalid handover contract: " + "; ".join(map(str, issues)))
    return source, raw, spec


def _build_handover(source: Path, raw: bytes, spec: dict[str, Any]) -> dict[str, Any]:
    findings = [f.to_dict() for f in check_spec(spec)]
    order = {code: index for index, code in enumerate(PRIORITY)}
    findings.sort(key=lambda f: (order.get(f["code"], len(order)), f["path"], f["code"]))
    questions = [dict(f, question=QUESTIONS.get(f["code"], f["message"] + " What answer resolves this gap?")) for f in findings]
    contacts = []
    for role, section, field in CONTACT_PATHS:
        value = spec.get(section, {}).get(field)
        contacts.append({"role": role, "path": f"$.{section}.{field}", "declared_value": value,
                         "status": "missing" if _missing(value) else "declared_not_confirmed"})
    return {
        "format": "interface-as-code-handover/1.0",
        "source": {"path": str(source), "sha256": hashlib.sha256(raw).hexdigest(),
                   "binding_scope": "Source YAML bytes only; referenced artifacts are not bundled or attested."},
        "interface": spec["interface"],
        "acceptance": {"status": "not_assessed", "replay_authority": "not_granted",
                       "test_execution": "not_performed", "evidence_verification": "not_performed"},
        "declared_contacts": contacts,
        "readiness": {"basis": "Built-in policies on this declaration; no overlay or policy-pack application.",
                      "counts": {level: sum(f["severity"] == level for f in findings) for level in ("error", "warning", "info")},
                      "questions": questions},
        "review_prompts": [
            {"path": "$.monitoring.owner", "question": "Has the declared team accepted this handover, including support access and escalation?"},
            {"path": "$.retry.replay", "question": "Before any replay, who authorizes it and how will duplicate effects and target business state be checked?"},
            {"path": "$.evidence", "question": "Which evidence covers this exact source/target and contract revision, and which checks remain unperformed?"},
        ],
        "declared_controls": control_model(spec),
        "proposed_test_plan": generate_test_plan(spec),
        "declared_references": {name: spec.get(name, {}) for name in ("contract", "mapping", "reconciliation")},
        "declared_evidence": spec.get("evidence", []),
        "limits": [
            "A generated report is not support acceptance or runtime evidence.",
            "A test purpose or expected result is a plan, not a test that ran or passed.",
            "Declared contacts have not been contacted or assigned by this report.",
            "Evidence references are not fetched, evaluated, or approved by this report.",
            "Changing a target or mapping requires review; prior evidence is not approval of the new declaration.",
            "Review prompts are unassessed questions, not additional policy failures.",
            "The report may contain internal contact and contract metadata; review before sharing.",
        ],
    }


def build_handover(path: str | Path) -> dict[str, Any]:
    """Load once, validate that same declaration, then reuse existing generators."""
    return _build_handover(*_load_contract(path))


def _text(value: Any) -> str:
    """Keep source values inert in Markdown, including HTML and multiline strings."""
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    # YAML can contain escaped lone surrogates; keep stdout valid UTF-8.
    text = text.encode("utf-8", errors="backslashreplace").decode("utf-8")
    text = html.escape(text, quote=False)
    for char in ("\\", "`", "*", "_", "{", "}", "[", "]", "(", ")", "#", "!", "|", ">"):
        text = text.replace(char, "\\" + char)
    return text


def render_handover(report: dict[str, Any]) -> str:
    counts = report["readiness"]["counts"]
    lines = ["# Support handover brief", "", f"Interface: {_text(report['interface']['id'])}",
             f"Declared source: {_text(report['interface']['source'])}",
             f"Declared target: {_text(report['interface']['target'])}",
             f"Mode: {_text(report['interface']['mode'])}. Contract format: {_text(report['proposed_test_plan']['contract_format'])}.",
             "", "**Declaration review only. Acceptance is not assessed; replay is not authorized.**", "",
             f"Source: {_text(report['source']['path'])}", f"Source SHA-256: {report['source']['sha256']}",
             "", "## Questions to resolve", "",
             f"Built-in readiness findings: errors {counts['error']}, warnings {counts['warning']}, information {counts['info']}.", ""]
    if not report["readiness"]["questions"]:
        lines.append("No built-in findings. This does not establish operational acceptance.")
    for q in report["readiness"]["questions"]:
        lines += [f"### {q['severity'].upper()}: {q['code']}", f"Contract path: {q['path']}", q['question'],
                  f"Why: {q['message']}", f"Next step: {q['remediation']}", ""]
    lines += ["## Declared contacts, not confirmed assignments", ""]
    for c in report["declared_contacts"]:
        lines.append(f"- {c['role']} ({c['path']}): {_text(c['declared_value'])}; {c['status']}.")
    lines += ["", "## Human review still required", ""]
    for q in report["review_prompts"]:
        lines.append(f"- {q['path']}: {q['question']}")
    lines += ["", "## Declared operational controls", "", "These reuse the existing controls model; they have not been exercised.", ""]
    for section in ("monitoring", "recovery", "reconciliation"):
        lines += [f"### {section.title()}"]
        for field, value in report["declared_controls"][section].items():
            lines.append(f"- {field}: {_text(value)}")
        lines.append("")
    lines += ["## Proposed checks, not executed tests", ""]
    for case in report["proposed_test_plan"]["cases"]:
        lines += [f"- {_text(case['id'])}: {_text(case['purpose'])} Expected if executed: {_text(case['expected'])}."]
    lines += ["", "## Declared references and evidence", "", "Not fetched, evaluated or approved by this report.", ""]
    for name, value in report["declared_references"].items():
        lines.append(f"- {name}: {_text(value)}")
    lines.append(f"- evidence: {_text(report['declared_evidence'])}")
    lines += ["", "## Limits", "", *[f"- {value}" for value in report["limits"]], ""]
    return "\n".join(lines)
