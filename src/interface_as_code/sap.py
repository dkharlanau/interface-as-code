from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any
import yaml

SAP_KEYS={"integration_style","technology","integration_assessment_ref","package_id","iflow_id","aif_namespace","aif_interface","drf_outbound_implementation","runtime_artifact_id"}

def sap_summary(spec:dict[str,Any])->dict[str,Any]:
    p=spec.get("profiles",{}).get("sap",{})
    return {"interface_id":spec["interface"]["id"],"contract":spec.get("contract",{}).get("format"),"message_type":spec.get("contract",{}).get("message_type"),"integration_style":p.get("integration_style"),"technology":p.get("technology"),"integration_assessment_ref":p.get("integration_assessment_ref"),"cloud_integration":{"package_id":p.get("package_id"),"iflow_id":p.get("iflow_id")},"aif":{"namespace":p.get("aif_namespace"),"interface":p.get("aif_interface")},"drf":{"outbound_implementation":p.get("drf_outbound_implementation")},"runtime_artifact_id":p.get("runtime_artifact_id"),"monitoring_owner":spec.get("monitoring",{}).get("owner"),"replay":spec.get("retry",{}).get("replay"),"reconciliation":spec.get("reconciliation",{})}

def apply_offline_metadata(spec:dict[str,Any],metadata:dict[str,Any])->tuple[dict[str,Any],list[str]]:
    out=deepcopy(spec);profile=out.setdefault("profiles",{}).setdefault("sap",{});ignored=[]
    for key,value in metadata.items():
        if key in SAP_KEYS:profile[key]=value
        else:ignored.append(str(key))
    return out,ignored

def load_offline_metadata(path:str|Path)->dict[str,Any]:
    data=yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(data,dict):raise ValueError("SAP metadata export must be a YAML/JSON object")
    return data

def render_sap_summary(spec:dict[str,Any],format_name:str="markdown")->str:
    model=sap_summary(spec)
    if format_name=="yaml":return yaml.safe_dump(model,sort_keys=False)
    ci,aif,drf=model["cloud_integration"],model["aif"],model["drf"]
    return "\n".join([f"# SAP integration profile — {model['interface_id']}","",f"- Integration style: **{model.get('integration_style') or 'TODO'}**",f"- Technology: **{model.get('technology') or 'TODO'}**",f"- Integration Assessment reference: `{model.get('integration_assessment_ref') or '—'}`",f"- Cloud Integration package/iFlow: `{ci.get('package_id') or '—'}` / `{ci.get('iflow_id') or '—'}`",f"- AIF namespace/interface: `{aif.get('namespace') or '—'}` / `{aif.get('interface') or '—'}`",f"- DRF outbound implementation: `{drf.get('outbound_implementation') or '—'}`",f"- Runtime artifact: `{model.get('runtime_artifact_id') or '—'}`","","## Operations","",f"- Monitoring owner: **{model.get('monitoring_owner') or 'TODO'}**",f"- Replay: {model.get('replay') or 'TODO'}",f"- Reconciliation key: `{model.get('reconciliation',{}).get('key') or 'TODO'}`",""])
