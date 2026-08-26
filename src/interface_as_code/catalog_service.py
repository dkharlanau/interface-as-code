from __future__ import annotations
import json
from pathlib import Path
from typing import Any

class CatalogService:
    def __init__(self, catalog_path: str | Path):
        path=Path(catalog_path)
        if path.is_dir():
            path=path/"index.json"
        self.path=path
        self.catalog=json.loads(path.read_text(encoding="utf-8"))
    def list(self) -> list[dict[str, Any]]:
        return list(self.catalog.get("interfaces", []))
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
