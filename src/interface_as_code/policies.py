from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    path: str
    message: str
    remediation: str
    def to_dict(self): return asdict(self)

PLACEHOLDERS = {"TODO", "TBD", "UNASSIGNED", "UNKNOWN", "TODO-SOURCE", "TODO-TARGET"}
def _missing(value: Any) -> bool:
    return value is None or value == "" or (isinstance(value,str) and value.strip().upper() in PLACEHOLDERS)
def _add(items, severity, code, path, message, remediation):
    items.append(Finding(severity, code, path, message, remediation))

def check_spec(spec: dict[str, Any]) -> list[Finding]:
    f: list[Finding] = []
    i=spec.get("interface",{}); own=spec.get("ownership",{}); d=spec.get("delivery",{}); idem=d.get("idempotency",{}); r=spec.get("retry",{}); m=spec.get("monitoring",{}); rec=spec.get("reconciliation",{}); sla=spec.get("sla",{}); sec=spec.get("security",{}); tests=spec.get("tests",[]); ev=spec.get("evidence",[])
    critical=i.get("criticality") in {"high","critical"}; active=i.get("lifecycle") in {None,"active"}
    if _missing(m.get("owner")): _add(f,"error","owner.missing","$.monitoring.owner","Operational owner is missing.","Assign the team accountable for failures.")
    if _missing(own.get("technical")): _add(f,"warning","owner.technical-missing","$.ownership.technical","Technical owner is missing.","Assign a technical owner for change review.")
    if _missing(own.get("business")): _add(f,"warning","owner.business-missing","$.ownership.business","Business owner is missing.","Assign a business owner for service impact decisions.")
    if critical and _missing(own.get("support")): _add(f,"error","owner.support-missing","$.ownership.support","Critical interface has no support owner.","Set a support owner/escalation team.")
    if i.get("mode")=="async" and r.get("strategy") in {None,"none"}: _add(f,"error","recoverability.retry-missing","$.retry.strategy","Async interface has no retry/recovery strategy.","Define manual or automatic recovery.")
    if r.get("strategy")=="automatic" and not r.get("max_attempts"): _add(f,"error","recoverability.retry-unbounded","$.retry.max_attempts","Automatic retry has no attempt limit.","Set max_attempts.")
    if d.get("guarantee")=="at-least-once" and not idem.get("required"): _add(f,"error","delivery.idempotency-required","$.delivery.idempotency.required","At-least-once delivery can create duplicates.","Require idempotent processing.")
    if idem.get("required") and _missing(idem.get("key")): _add(f,"error","delivery.idempotency-key-missing","$.delivery.idempotency.key","Idempotency is required but no key is declared.","Define a stable idempotency key.")
    if critical and i.get("mode")=="async" and _missing(r.get("dead_letter")): _add(f,"warning","recoverability.dead-letter-missing","$.retry.dead_letter","Critical async interface has no dead-letter/error queue.","Declare where failed messages are retained.")
    if i.get("mode") in {"async","batch"} and _missing(r.get("replay")): _add(f,"warning","recoverability.replay-guidance-missing","$.retry.replay","Replay procedure is not documented.","Describe safe replay/reprocessing steps.")
    if not m.get("signals"): _add(f,"warning","observability.signals-missing","$.monitoring.signals","No monitoring signals are declared.","Declare technical and business failure signals.")
    if critical and len(m.get("signals",[]))<2: _add(f,"warning","observability.critical-signal-coverage","$.monitoring.signals","Critical interface has weak signal coverage.","Track failures plus latency/backlog/business failures.")
    if _missing(m.get("business_key")): _add(f,"warning","observability.business-key-missing","$.monitoring.business_key","No business correlation key is declared.","Declare the business key used in logs/traces.")
    if _missing(rec.get("comparison")): _add(f,"warning","reconciliation.comparison-missing","$.reconciliation.comparison","Reconciliation describes no concrete comparison.","State what source and target populations/values are compared.")
    if critical and _missing(rec.get("key")): _add(f,"error","reconciliation.key-missing","$.reconciliation.key","Critical interface has no reconciliation key.","Declare a stable business reconciliation key.")
    if critical and not sla: _add(f,"warning","sla.missing","$.sla","High/critical interface has no service expectations.","Define expected latency and recovery target.")
    if critical and _missing(sla.get("recovery_target")): _add(f,"warning","sla.recovery-target-missing","$.sla.recovery_target","Critical interface has no recovery target.","Define maximum acceptable recovery time.")
    if not tests: _add(f,"warning","tests.missing","$.tests","No tests are declared.","Add happy-path plus failure/replay tests.")
    if active and not tests: _add(f,"error","tests.active-without-tests","$.tests","Active interface has no declared test intent.","Add test scenarios before treating it as production-ready.")
    if active and not ev: _add(f,"info","evidence.missing","$.evidence","No external test/runtime evidence is linked.","Link CI/JUnit/runtime evidence when available.")
    if sec.get("external_exposure") and _missing(sec.get("authentication")): _add(f,"error","security.auth-missing","$.security.authentication","Externally exposed interface has no authentication metadata.","Reference the authentication mechanism; never store secrets.")
    if sec.get("personal_data") and sec.get("transport_encryption") is not True: _add(f,"error","security.encryption-required","$.security.transport_encryption","Personal data is not explicitly protected in transport.","Require transport encryption.")
    if critical and _missing(sec.get("data_classification")): _add(f,"warning","security.classification-missing","$.security.data_classification","Critical interface has no data classification.","Classify transported data.")
    if d.get("guarantee")=="best-effort" and critical: _add(f,"error","delivery.best-effort-critical","$.delivery.guarantee","Critical interface uses best-effort delivery.","Use a stronger delivery model or justify via policy exception.")
    if i.get("mode")=="sync" and r.get("strategy")=="manual": _add(f,"info","retry.sync-manual","$.retry.strategy","Sync API declares manual retry.","Clarify whether caller or operator owns retries.")
    if _missing(m.get("support_route")): _add(f,"error","support.route-missing","$.monitoring.support_route","No support route is declared.","Declare the operational queue/tool/runbook entry point.")
    if not spec.get("mapping",{}): _add(f,"warning","mapping.missing","$.mapping","No mapping artifact/profile is declared.","Reference mapping logic or explicitly state identity/no mapping.")
    if i.get("mode")=="batch" and not spec.get("trigger",{}).get("schedule"): _add(f,"warning","batch.schedule-missing","$.trigger.schedule","Batch interface has no schedule.","Declare expected batch cadence.")
    return f
