from __future__ import annotations
import hashlib, json
from copy import deepcopy
from pathlib import Path
from typing import Any

class CatalogService:
    def __init__(self, catalog_path: str | Path):
        path=Path(catalog_path)
        if path.is_dir():
            path=path/"index.json"
        self.path=path
        raw=path.read_bytes()
        self.catalog=json.loads(raw.decode("utf-8"))
        self.snapshot_sha256=hashlib.sha256(raw).hexdigest()
    def list(self) -> list[dict[str, Any]]:
        return [deepcopy({k: v for k, v in item.items() if k != "handover"}) for item in self.catalog.get("interfaces", [])]
    def search(self, query: str) -> list[dict[str, Any]]:
        q=query.lower().strip()
        if not q:
            return self.list()
        fields=("id","name","source","protocol","criticality","lifecycle","owner","business_object")
        out=[]
        for item in self.list():
            hay=" ".join(str(item.get(f,"")) for f in fields)+" "+" ".join(item.get("targets",[]))
            if q in hay.lower():
                out.append(item)
        return out
    def get(self, interface_id: str) -> dict[str, Any] | None:
        return next((x for x in self.list() if x.get("id")==interface_id),None)
    def status(self) -> dict[str, Any]:
        return deepcopy({"catalog_path":str(self.path),"summary":self.catalog.get("summary",{}),"invalid":self.catalog.get("invalid",[])})
    def operations(self, interface_id: str) -> dict[str, Any] | None:
        item=self.get(interface_id)
        if not item:return None
        return {"id":item["id"],"operations":item.get("operations",{}),"findings":item.get("findings",{}),"provenance":item.get("provenance",{"path":item.get("path")})}

    def handover(self, interface_id: str) -> dict[str, Any]:
        """Read a retained projection only; never reopen a source or referenced artifact."""
        matches = [x for x in self.catalog.get("interfaces", []) if x.get("id") == interface_id]
        if len(matches) > 1:
            return {"error": "ambiguous_interface_id", "interface_id": interface_id,
                    "next_step": "Resolve duplicate identifiers before requesting a handover."}
        item = matches[0] if matches else None
        if item is None:
            return {"error": "not_found", "interface_id": interface_id}
        if "handover" not in item:
            return {"error": "handover_not_in_catalog", "interface_id": interface_id,
                    "next_step": "Regenerate the catalog with --include-handover; absence is not a clean review."}
        return {"interface_id": interface_id, "handover": deepcopy(item["handover"]),
                "provenance": deepcopy(item.get("provenance", {})),
                "catalog_snapshot": {"sha256": self.snapshot_sha256, "freshness": "not_checked",
                                     "scope": "Catalog bytes loaded when this service started; not a signature or current-state check."}}
