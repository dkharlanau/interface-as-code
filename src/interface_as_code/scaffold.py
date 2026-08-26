from __future__ import annotations

from pathlib import Path
from typing import Any
from .loader import dump_yaml

PROFILES = ("sap-idoc", "rest-api", "event", "file-batch", "b2b-edi")

def _base(interface_id: str, name: str, source: str, target: str) -> dict[str, Any]:
    return {
        "version": "1.0",
        "interface": {"id": interface_id, "name": name, "source": {"system": source}, "target": {"system": target}, "mode": "async", "criticality": "medium", "lifecycle": "proposed"},
        "ownership": {"business": "TODO", "technical": "TODO", "support": "TODO"},
        "trigger": {"event": "TODO"},
        "contract": {"format": "JSON"},
        "delivery": {"guarantee": "at-least-once", "ordering": "none", "idempotency": {"required": True, "key": "TODO"}},
        "mapping": {"profile": "TODO"},
        "retry": {"strategy": "manual", "replay": "TODO"},
        "monitoring": {"owner": "TODO", "support_route": "TODO", "business_key": "TODO", "signals": ["technical_failure"]},
        "reconciliation": {"key": "TODO", "frequency": "daily", "source_of_truth": source, "comparison": "TODO"},
        "tests": [{"id": "happy-path", "description": "TODO", "expected": "processed"}],
    }

def profile_spec(profile: str, interface_id: str, name: str, source: str = "SOURCE", target: str = "TARGET") -> dict[str, Any]:
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile {profile}. Choose from: {', '.join(PROFILES)}")
    spec = _base(interface_id, name, source, target)
    i = spec["interface"]
    if profile == "sap-idoc":
        i.update({"pattern": "message-driven", "tags": ["sap", "idoc"]})
        spec["contract"] = {"format": "IDoc", "message_type": "TODO", "basic_type": "TODO"}
        spec["route"] = {"middleware": ["TODO"]}
        spec["mapping"] = {"file": "mapping.yaml", "profile": "core"}
        spec["retry"]["dead_letter"] = "TODO operational error queue"
    elif profile == "rest-api":
        i.update({"mode": "sync", "pattern": "request-response", "tags": ["rest", "api"]})
        spec["trigger"] = {"operation": "POST /resource"}
        spec["contract"] = {"format": "REST", "content_type": "application/json"}
        spec["retry"] = {"strategy": "none"}
        spec["delivery"] = {"guarantee": "effectively-once", "ordering": "none", "idempotency": {"required": True, "key": "Idempotency-Key"}}
    elif profile == "event":
        i.update({"mode": "async", "pattern": "event-driven", "tags": ["event"]})
        spec["contract"] = {"format": "Kafka", "content_type": "application/json"}
        spec["retry"] = {"strategy": "automatic", "max_attempts": 5, "backoff": "exponential", "dead_letter": "TODO DLQ", "replay": "Replay from retained event stream."}
    elif profile == "file-batch":
        i.update({"mode": "batch", "pattern": "file-transfer", "tags": ["file", "batch"]})
        spec["trigger"] = {"schedule": "daily"}
        spec["contract"] = {"format": "CSV", "content_type": "text/csv"}
        spec["retry"] = {"strategy": "manual", "replay": "Re-submit the same batch after correction."}
    elif profile == "b2b-edi":
        i.update({"mode": "async", "pattern": "message-driven", "tags": ["b2b", "edi"]})
        spec["contract"] = {"format": "EDI", "message_type": "ORDERS"}
        spec["security"] = {"authentication": "TODO", "transport_encryption": True, "data_classification": "confidential", "external_exposure": True}
    return spec

def write_profile(directory: str | Path, profile: str, interface_id: str, name: str, source: str = "SOURCE", target: str = "TARGET") -> Path:
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    spec = profile_spec(profile, interface_id, name, source, target)
    path = root / "interface.yaml"
    dump_yaml(spec, path)
    if profile == "sap-idoc":
        dump_yaml({"version": "1.0", "profile": "core", "fields": []}, root / "mapping.yaml")
    return path
