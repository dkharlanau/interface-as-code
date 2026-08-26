from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class Change:
    path: str; old: Any; new: Any; severity: str; reason: str
    def to_dict(self): return asdict(self)

def _flatten(value: Any, prefix: str = "$") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(value, dict):
        if not value: out[prefix] = {}
        for k,v in value.items(): out.update(_flatten(v, f"{prefix}.{k}"))
    elif isinstance(value, list):
        out[prefix] = value
    else: out[prefix] = value
    return out

def classify(path: str, old: Any, new: Any) -> tuple[str,str]:
    breaking_prefixes=("$.interface.source","$.interface.target","$.interface.consumers","$.contract.format","$.contract.message_type","$.contract.basic_type","$.contract.schema_ref","$.contract.ref","$.reconciliation.key")
    risky_prefixes=("$.delivery.","$.retry.","$.reconciliation.source_of_truth","$.sla.","$.security.")
    review_prefixes=("$.ownership.","$.monitoring.owner","$.monitoring.support_route","$.interface.lifecycle","$.route.")
    if path.startswith(breaking_prefixes): return "breaking", "Contract/topology or reconciliation identity changed."
    if path.startswith(risky_prefixes): return "high-risk", "Runtime delivery, recovery, service or security behavior changed."
    if path.startswith(review_prefixes): return "review", "Ownership, lifecycle or operational routing changed."
    if path.startswith("$.monitoring.signals"): return "informational", "Observability coverage changed."
    if path.startswith(("$.interface.description","$.interface.tags","$.tests","$.evidence")): return "informational", "Documentation/test/evidence metadata changed."
    return "review", "Specification semantics changed and should be reviewed."

def semantic_diff(old: dict[str, Any], new: dict[str, Any]) -> list[Change]:
    a,b=_flatten(old),_flatten(new); changes=[]
    for path in sorted(set(a)|set(b)):
        if a.get(path)!=b.get(path):
            severity,reason=classify(path,a.get(path),b.get(path)); changes.append(Change(path,a.get(path),b.get(path),severity,reason))
    return changes
