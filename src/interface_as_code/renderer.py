from __future__ import annotations
from typing import Any

def _value(value: Any, default: str = "—") -> str:
    if value is None or value == "": return default
    if isinstance(value,bool): return "yes" if value else "no"
    if isinstance(value,list): return ", ".join(str(x) for x in value) or default
    return str(value)

def render_mermaid(spec: dict[str, Any]) -> str:
    i=spec["interface"]; source=i["source"]["system"]; targets=i.get("consumers") or [i["target"]]; trigger=spec.get("trigger",{}); event=trigger.get("event") or trigger.get("operation") or trigger.get("schedule") or "trigger"; message=spec["contract"].get("message_type") or spec["contract"]["format"]
    lines=["sequenceDiagram",f"    participant S as {source}",f"    Note over S: {event}"]
    for n,t in enumerate(targets,1): lines += [f"    participant T{n} as {t['system']}",f"    S->>T{n}: {message}",f"    T{n}-->>S: processing outcome"]
    return "\n".join(lines)

def render_markdown(spec: dict[str, Any]) -> str:
    i=spec["interface"]; own=spec.get("ownership",{}); c=spec["contract"]; d=spec.get("delivery",{}); r=spec.get("retry",{}); m=spec.get("monitoring",{}); rec=spec.get("reconciliation",{}); sec=spec.get("security",{}); targets=i.get("consumers") or [i["target"]]
    lines=[f"# {i['name']}","",f"`{i['id']}` · spec `{spec['version']}` · lifecycle **{_value(i.get('lifecycle'))}**","","## Topology","",f"- Source: **{i['source']['system']}**",f"- Target(s): **{', '.join(t['system'] for t in targets)}**",f"- Mode/pattern: **{i['mode']} / {_value(i.get('pattern'))}**","","## Ownership","",f"- Business: **{_value(own.get('business'))}**",f"- Technical: **{_value(own.get('technical'))}**",f"- Support: **{_value(own.get('support') or m.get('owner'))}**","","## Contract","",f"- Format: **{c['format']}**",f"- Message/schema: **{_value(c.get('message_type') or c.get('schema_ref'))}**","","## Delivery and recovery","",f"- Guarantee: **{_value(d.get('guarantee'))}**",f"- Idempotency: **{_value(d.get('idempotency',{}).get('required'))}** / `{_value(d.get('idempotency',{}).get('key'))}`",f"- Retry: **{_value(r.get('strategy'))}**",f"- Replay: {_value(r.get('replay'))}","","## Operations","",f"- Monitor owner: **{_value(m.get('owner'))}**",f"- Support route: **{_value(m.get('support_route'))}**",f"- Signals: {_value(m.get('signals'))}","","## Reconciliation","",f"- Key: `{_value(rec.get('key'))}`",f"- Frequency: **{_value(rec.get('frequency'))}**",f"- Source of truth: **{_value(rec.get('source_of_truth'))}**",f"- Comparison: {_value(rec.get('comparison'))}","","## Security","",f"- Classification: **{_value(sec.get('data_classification'))}**",f"- Authentication: **{_value(sec.get('authentication'))}**",f"- Transport encryption: **{_value(sec.get('transport_encryption'))}**","","## Flow","","```mermaid",render_mermaid(spec),"```",""]
    return "\n".join(lines)
