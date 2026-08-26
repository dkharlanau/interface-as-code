from __future__ import annotations
from typing import Any
import yaml

HTTP_REF="https://opentelemetry.io/docs/specs/semconv/http/"
MESSAGING_REF="https://opentelemetry.io/docs/specs/semconv/messaging/"

def requirements(spec:dict[str,Any])->dict[str,Any]:
    i=spec["interface"];c=spec["contract"];m=spec.get("monitoring",{});mode,fmt=i.get("mode"),c.get("format");correlation=m.get("business_key") or spec.get("reconciliation",{}).get("key");signals=list(dict.fromkeys(m.get("signals",[])));conventions=[];required=["failures","throughput"];attrs=["interface.id","business.key"]
    if fmt in {"REST","OData","SOAP"}:
        required += ["latency","status/outcome"];conventions.append({"family":"OpenTelemetry HTTP semantic conventions","status":"Mixed","reference":HTTP_REF,"version_policy":"pin in implementation adapter"});attrs += ["http.request.method","http.response.status_code"]
    elif fmt in {"Kafka","JMS"} or mode=="async":
        required += ["processing latency","consumer lag/backlog","retries","dead letters"];conventions.append({"family":"OpenTelemetry messaging semantic conventions","status":"Development","reference":MESSAGING_REF,"version_policy":"pin in implementation adapter"});attrs += ["messaging.system","messaging.destination.name","messaging.operation.type"]
    elif mode=="batch" or fmt in {"CSV","File","EDI"}:
        required += ["batch age","records accepted/rejected","missing/late batch"];attrs += ["batch.id","file.name"]
    required += [s for s in signals if s not in required]
    return {"interface_id":i["id"],"owner":m.get("owner"),"correlation":{"business_key":correlation,"required":bool(correlation)},"required_signals":required,"recommended_attributes":attrs,"semantic_conventions":conventions,"vendor_neutral":True}

def render(spec:dict[str,Any],format_name:str="markdown")->str:
    model=requirements(spec)
    if format_name=="yaml":return yaml.safe_dump(model,sort_keys=False)
    lines=[f"# Observability requirements — {model['interface_id']}","",f"- Owner: **{model.get('owner') or 'TODO'}**",f"- Correlation key: `{model['correlation'].get('business_key') or 'TODO'}`","","## Required signals","",*[f"- {x}" for x in model["required_signals"]],"","## Recommended attributes","",*[f"- `{x}`" for x in model["recommended_attributes"]],"","## Standards alignment",""]
    if model["semantic_conventions"]:
        for item in model["semantic_conventions"]:lines.append(f"- {item['family']} — status **{item['status']}**; {item['version_policy']}; {item['reference']}")
    else:lines.append("- No protocol-specific convention required.")
    return "\n".join(lines)+"\n"
