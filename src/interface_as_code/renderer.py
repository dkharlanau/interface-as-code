from __future__ import annotations

from typing import Any


def _value(value: Any, default: str = "—") -> str:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) or default
    return str(value)


def render_mermaid(spec: dict[str, Any]) -> str:
    interface = spec["interface"]
    trigger = spec.get("trigger", {})
    source = interface["source"]["system"]
    target = interface["target"]["system"]
    event = trigger.get("event") or trigger.get("schedule") or "trigger"
    message = spec["contract"].get("message_type") or spec["contract"]["format"]

    return "\n".join(
        [
            "sequenceDiagram",
            f"    participant S as {source}",
            f"    participant T as {target}",
            f"    Note over S: {event}",
            f"    S->>T: {message}",
            "    T-->>S: processing outcome",
        ]
    )


def render_markdown(spec: dict[str, Any]) -> str:
    interface = spec["interface"]
    contract = spec["contract"]
    delivery = spec.get("delivery", {})
    retry = spec.get("retry", {})
    monitoring = spec.get("monitoring", {})
    reconciliation = spec.get("reconciliation", {})
    mapping = spec.get("mapping", {})
    sla = spec.get("sla", {})

    lines = [
        f"# {interface['name']}",
        "",
        f"`{interface['id']}` · specification version `{spec['version']}`",
        "",
        "## Interface",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Source | {_value(interface['source']['system'])} / {_value(interface['source'].get('object'))} |",
        f"| Target | {_value(interface['target']['system'])} / {_value(interface['target'].get('object'))} |",
        f"| Mode | {_value(interface['mode'])} |",
        f"| Pattern | {_value(interface.get('pattern'))} |",
        f"| Criticality | {_value(interface.get('criticality'))} |",
        "",
        "## Contract",
        "",
        f"- Format: **{_value(contract.get('format'))}**",
        f"- Message type: **{_value(contract.get('message_type'))}**",
        f"- Schema/reference: `{_value(contract.get('schema_ref'))}`",
        "",
        "## Delivery semantics",
        "",
        f"- Guarantee: **{_value(delivery.get('guarantee'))}**",
        f"- Ordering: **{_value(delivery.get('ordering'))}**",
        f"- Idempotency required: **{_value(delivery.get('idempotency', {}).get('required'))}**",
        f"- Idempotency key: `{_value(delivery.get('idempotency', {}).get('key'))}`",
        "",
        "## Mapping",
        "",
        f"- Mapping file: `{_value(mapping.get('file'))}`",
        f"- Mapping profile: `{_value(mapping.get('profile'))}`",
        "",
        "## Retry and failure handling",
        "",
        f"- Strategy: **{_value(retry.get('strategy'))}**",
        f"- Max attempts: **{_value(retry.get('max_attempts'))}**",
        f"- Dead-letter route: `{_value(retry.get('dead_letter'))}`",
        "",
        "## Operations",
        "",
        f"- Owner: **{_value(monitoring.get('owner'))}**",
        f"- Support route: **{_value(monitoring.get('support_route'))}**",
        f"- Signals: {_value(monitoring.get('signals'))}",
        "",
        "## Reconciliation",
        "",
        f"- Key: `{_value(reconciliation.get('key'))}`",
        f"- Frequency: **{_value(reconciliation.get('frequency'))}**",
        f"- Source of truth: **{_value(reconciliation.get('source_of_truth'))}**",
        "",
        "## Service expectation",
        "",
        f"- Expected latency: **{_value(sla.get('expected_latency'))}**",
        f"- Recovery target: **{_value(sla.get('recovery_target'))}**",
        "",
        "## Flow",
        "",
        "```mermaid",
        render_mermaid(spec),
        "```",
        "",
    ]
    return "\n".join(lines)
