from __future__ import annotations

from typing import Any
import yaml


def control_model(spec: dict[str, Any]) -> dict[str, Any]:
    i = spec["interface"]
    monitoring = spec.get("monitoring", {})
    retry = spec.get("retry", {})
    reconciliation = spec.get("reconciliation", {})
    delivery = spec.get("delivery", {})
    return {
        "interface_id": i["id"],
        "monitoring": {"owner": monitoring.get("owner"), "support_route": monitoring.get("support_route"), "business_key": monitoring.get("business_key") or reconciliation.get("key"), "required_signals": monitoring.get("signals", [])},
        "recovery": {"strategy": retry.get("strategy"), "max_attempts": retry.get("max_attempts"), "dead_letter": retry.get("dead_letter"), "replay": retry.get("replay"), "idempotency_required": delivery.get("idempotency", {}).get("required"), "idempotency_key": delivery.get("idempotency", {}).get("key")},
        "reconciliation": {"key": reconciliation.get("key"), "frequency": reconciliation.get("frequency"), "source_of_truth": reconciliation.get("source_of_truth"), "comparison": reconciliation.get("comparison")},
    }


def render_controls(spec: dict[str, Any], format_name: str = "markdown") -> str:
    model = control_model(spec)
    if format_name == "yaml":
        return yaml.safe_dump(model, sort_keys=False, allow_unicode=True)
    m, r, rec = model["monitoring"], model["recovery"], model["reconciliation"]
    lines = [f"# Operational controls — {model['interface_id']}", "", "## Monitoring requirements", "", f"- Owner: **{m.get('owner') or 'TODO'}**", f"- Support route: **{m.get('support_route') or 'TODO'}**", f"- Correlation/business key: `{m.get('business_key') or 'TODO'}`", f"- Required signals: {', '.join(m.get('required_signals') or []) or 'TODO'}", "", "## Recovery runbook", "", f"- Retry strategy: **{r.get('strategy') or 'TODO'}**", f"- Maximum attempts: **{r.get('max_attempts') or 'n/a'}**", f"- Dead-letter/error route: **{r.get('dead_letter') or 'TODO'}**", f"- Replay procedure: {r.get('replay') or 'TODO'}", f"- Idempotency: **{r.get('idempotency_required')}** using `{r.get('idempotency_key') or 'TODO'}`", "", "## Reconciliation control", "", f"- Key: `{rec.get('key') or 'TODO'}`", f"- Frequency: **{rec.get('frequency') or 'TODO'}**", f"- Source of truth: **{rec.get('source_of_truth') or 'TODO'}**", f"- Comparison: {rec.get('comparison') or 'TODO'}", ""]
    return "\n".join(lines)
