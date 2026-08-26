from __future__ import annotations
from typing import Any
import yaml


def backstage_entity(spec:dict[str,Any])->dict[str,Any]:
    i=spec["interface"];owner=spec.get("ownership",{}).get("technical") or spec.get("monitoring",{}).get("owner") or "unknown";targets=i.get("consumers") or [i["target"]]
    return {"apiVersion":"backstage.io/v1alpha1","kind":"Resource","metadata":{"name":i["id"].lower().replace("_","-").replace(".","-"),"title":i["name"],"description":i.get("description","Enterprise integration interface managed as code."),"tags":[str(x).lower() for x in i.get("tags",[])],"annotations":{"interface-as-code/id":i["id"],"interface-as-code/source":i["source"]["system"],"interface-as-code/targets":",".join(t["system"] for t in targets)}},"spec":{"type":"integration-interface","owner":owner,"lifecycle":i.get("lifecycle","production"),"system":i["source"]["system"],"dependencyOf":[t["system"] for t in targets]}}

def leanix_interface_export(spec:dict[str,Any])->dict[str,Any]:
    i=spec["interface"];c=spec["contract"];targets=i.get("consumers") or [i["target"]]
    return {"externalId":i["id"],"name":i["name"],"description":i.get("description"),"lifecycle":i.get("lifecycle"),"criticality":i.get("criticality"),"provider":i["source"]["system"],"consumers":[t["system"] for t in targets],"interfaceTechnology":c.get("format"),"businessObject":i.get("source",{}).get("object"),"owner":spec.get("ownership",{}).get("business") or spec.get("monitoring",{}).get("owner"),"sourceOfTruth":"Interface as Code","sourceInterfaceId":i["id"]}

def compare_leanix_snapshot(spec:dict[str,Any],payload:dict[str,Any])->list[dict[str,Any]]:
    """Treat LeanIX input as catalog evidence; never overwrite the operational spec."""
    expected=leanix_interface_export(spec);fields=("externalId","name","lifecycle","criticality","provider","consumers","interfaceTechnology","businessObject","owner");out=[]
    for field in fields:
        if field in payload and payload.get(field)!=expected.get(field):out.append({"field":field,"interface_as_code":expected.get(field),"leanix":payload.get(field),"status":"different"})
    return out

def render_adapter(spec:dict[str,Any],adapter:str)->str:
    if adapter=="backstage":return yaml.safe_dump(backstage_entity(spec),sort_keys=False,allow_unicode=True)
    if adapter=="leanix":return yaml.safe_dump(leanix_interface_export(spec),sort_keys=False,allow_unicode=True)
    raise ValueError(f"Unknown adapter: {adapter}")
