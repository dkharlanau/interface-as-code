from __future__ import annotations
from copy import deepcopy
from typing import Any

SUPPORTED_SPEC_VERSIONS=("1.0",)

def migrate_spec(spec:dict[str,Any],target_version:str)->tuple[dict[str,Any],list[str]]:
    source=str(spec.get("version",""))
    if source not in SUPPORTED_SPEC_VERSIONS:raise ValueError(f"Unsupported source specification version: {source}")
    if target_version not in SUPPORTED_SPEC_VERSIONS:raise ValueError(f"Unsupported target specification version: {target_version}")
    if source==target_version:return deepcopy(spec),["No migration required; source already matches target specification version."]
    raise ValueError(f"No deterministic migration path from {source} to {target_version}")
