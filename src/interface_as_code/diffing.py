from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import subprocess, yaml
from .loader import load_yaml

@dataclass(frozen=True)
class Change:
    path:str; old:Any; new:Any; severity:str; reason:str
    def to_dict(self):return asdict(self)

def _flatten(value:Any,prefix:str="$" )->dict[str,Any]:
    out={}
    if isinstance(value,dict):
        if not value:out[prefix]={}
        for k,v in value.items():out.update(_flatten(v,f"{prefix}.{k}"))
    elif isinstance(value,list):out[prefix]=value
    else:out[prefix]=value
    return out

def classify(path:str,old:Any,new:Any)->tuple[str,str]:
    breaking=("$.interface.source","$.interface.target","$.interface.consumers","$.contract.format","$.contract.message_type","$.contract.basic_type","$.contract.schema_ref","$.contract.ref","$.reconciliation.key")
    risky=("$.delivery.","$.retry.","$.reconciliation.source_of_truth","$.sla.","$.security.")
    review=("$.ownership.","$.monitoring.owner","$.monitoring.support_route","$.interface.lifecycle","$.route.")
    if path.startswith(breaking):return "breaking","Contract/topology or reconciliation identity changed."
    if path.startswith(risky):return "high-risk","Runtime delivery, recovery, service or security behavior changed."
    if path.startswith(review):return "review","Ownership, lifecycle or operational routing changed."
    if path.startswith("$.monitoring.signals"):return "informational","Observability coverage changed."
    if path.startswith(("$.interface.description","$.interface.tags","$.tests","$.evidence")):return "informational","Documentation/test/evidence metadata changed."
    return "review","Specification semantics changed and should be reviewed."

def semantic_diff(old:dict[str,Any],new:dict[str,Any])->list[Change]:
    a,b=_flatten(old),_flatten(new);out=[]
    for path in sorted(set(a)|set(b)):
        if a.get(path)!=b.get(path):severity,reason=classify(path,a.get(path),b.get(path));out.append(Change(path,a.get(path),b.get(path),severity,reason))
    return out

def load_spec_source(source:str)->dict[str,Any]:
    if Path(source).exists():return load_yaml(source)
    if ":" not in source:raise ValueError(f"Not a file or git ref:path source: {source}")
    rev,path=source.split(":",1)
    proc=subprocess.run(["git","show",f"{rev}:{path}"],capture_output=True,text=True,check=False)
    if proc.returncode:raise ValueError(proc.stderr.strip() or f"Cannot read {source}")
    data=yaml.safe_load(proc.stdout)
    if not isinstance(data,dict):raise ValueError(f"{source} does not contain a YAML object")
    return data
