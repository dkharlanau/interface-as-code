from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import yaml
from .loader import dump_yaml

@dataclass
class ImportGap:
    row: int
    interface_id: str
    field: str
    message: str

def _slug(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-")
    return value or "interface"

def _id(value: str, row: int) -> str:
    candidate = _slug(value).upper()
    if len(candidate) < 3:
        candidate = f"IF-{row:03d}"
    return candidate[:64]

def _protocol(value: str) -> str:
    lookup = {"idoc":"IDoc", "rest":"REST", "api":"REST", "odata":"OData", "soap":"SOAP", "kafka":"Kafka", "jms":"JMS", "csv":"CSV", "json":"JSON", "xml":"XML", "edi":"EDI", "file":"File", "sftp":"File"}
    return lookup.get(value.strip().lower(), value.strip() or "File")

def import_csv(csv_path: str | Path, output_dir: str | Path, column_map: dict[str, str] | None = None, system_map: dict[str, str] | None = None) -> dict[str, Any]:
    column_map = column_map or {}
    system_map = system_map or {}
    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
    gaps: list[ImportGap] = []
    generated: list[str] = []
    seen: set[str] = set()
    with Path(csv_path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row_no, row in enumerate(reader, 2):
            def get(name: str, default: str = "") -> str:
                return str(row.get(column_map.get(name, name), default) or "").strip()
            iid = _id(get("interface_id"), row_no)
            if iid in seen:
                gaps.append(ImportGap(row_no, iid, "interface_id", "Duplicate interface ID; row skipped.")); continue
            seen.add(iid)
            name = get("name") or f"Imported interface {iid}"
            if len(name) < 3: name = f"{name} interface"
            source = system_map.get(get("source"), get("source")) or "TODO-SOURCE"
            target = system_map.get(get("target"), get("target")) or "TODO-TARGET"
            owner = get("owner") or "TODO"
            support = get("support_route") or "TODO"
            business_key = get("business_key") or "TODO"
            protocol = _protocol(get("protocol"))
            mode = get("mode").lower() or ("batch" if protocol in {"CSV","File"} else "async")
            if mode not in {"sync","async","batch"}: mode = "async"
            contract: dict[str, Any] = {"format": protocol if protocol in {"IDoc","SOAP","REST","OData","Kafka","JMS","CSV","JSON","XML","EDI","File"} else "File"}
            if contract["format"] == "IDoc": contract["message_type"] = get("message_type") or "TODO"
            spec = {
                "version":"1.0",
                "interface":{"id":iid,"name":name,"source":{"system":source},"target":{"system":target},"mode":mode,"criticality":get("criticality").lower() if get("criticality").lower() in {"low","medium","high","critical"} else "medium","lifecycle":"proposed"},
                "ownership":{"business":get("business_owner") or "TODO","technical":get("technical_owner") or "TODO","support":owner},
                "trigger":{"schedule":get("frequency") or "TODO"} if mode == "batch" else {"event":"TODO"},
                "contract":contract,
                "delivery":{"guarantee":"at-least-once" if mode != "sync" else "effectively-once","ordering":"none","idempotency":{"required":True,"key":business_key}},
                "mapping":{"profile":"imported"},
                "retry":{"strategy":"manual" if mode != "sync" else "none","replay":"TODO"} if mode != "sync" else {"strategy":"none"},
                "monitoring":{"owner":owner,"support_route":support,"business_key":business_key,"signals":["technical_failure"]},
                "reconciliation":{"key":business_key,"frequency":get("reconciliation_frequency") or "daily","source_of_truth":source,"comparison":"TODO"}
            }
            middleware = get("middleware")
            if middleware: spec["route"] = {"middleware":[middleware]}
            for field, val in (("source",get("source")),("target",get("target")),("owner",get("owner")),("support_route",get("support_route")),("business_key",get("business_key"))):
                if not val: gaps.append(ImportGap(row_no, iid, field, "Missing in source inventory; explicit TODO placeholder generated."))
            folder = output / iid.lower(); dump_yaml(spec, folder / "interface.yaml")
            generated.append(str(folder / "interface.yaml"))
    report = {"source": str(csv_path), "generated": generated, "gaps": [asdict(g) for g in gaps]}
    (output / "import-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report

def load_mapping(path: str | Path | None) -> dict[str, str]:
    if not path: return {}
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict): raise ValueError("Mapping file must be a YAML object")
    return {str(k):str(v) for k,v in data.items()}
