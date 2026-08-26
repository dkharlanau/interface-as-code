from __future__ import annotations
import html, json
from collections import Counter
from pathlib import Path
from typing import Any
from .loader import load_yaml
from .validator import discover_specs, validate_spec
from .policies import check_spec

def _targets(spec):
    i=spec["interface"]
    return i.get("consumers") or [i["target"]]

def build_catalog(root: str | Path, output: str | Path) -> dict[str, Any]:
    out=Path(output); out.mkdir(parents=True,exist_ok=True); details=out/"interfaces"; details.mkdir(exist_ok=True)
    records=[]; invalid=[]
    for path in discover_specs(root):
        issues=validate_spec(path)
        if issues:
            invalid.append({"path":str(path),"issues":[str(x) for x in issues]}); continue
        spec=load_yaml(path); i=spec["interface"]; findings=check_spec(spec)
        record={"id":i["id"],"name":i["name"],"source":i["source"]["system"],"targets":[t["system"] for t in _targets(spec)],"mode":i["mode"],"protocol":spec["contract"]["format"],"criticality":i.get("criticality",""),"lifecycle":i.get("lifecycle",""),"owner":spec.get("monitoring",{}).get("owner",""),"business_object":i.get("source",{}).get("object",""),"findings":dict(Counter(x.severity for x in findings)),"path":str(path)}
        records.append(record)
        body=f"<h1>{html.escape(i['name'])}</h1><p><code>{html.escape(i['id'])}</code></p><p>{html.escape(record['source'])} → {html.escape(', '.join(record['targets']))}</p><h2>Readiness</h2><ul>"+"".join(f"<li><strong>{html.escape(x.severity)}</strong> {html.escape(x.code)} — {html.escape(x.message)}</li>" for x in findings)+"</ul>"
        (details/f"{i['id']}.html").write_text("<!doctype html><meta charset='utf-8'><title>"+html.escape(i['name'])+"</title>"+body,encoding="utf-8")
    summary={"total":len(records),"invalid":len(invalid),"protocols":dict(Counter(x["protocol"] for x in records)),"criticality":dict(Counter(x["criticality"] for x in records))}
    index={"summary":summary,"interfaces":records,"invalid":invalid}
    (out/"index.json").write_text(json.dumps(index,indent=2),encoding="utf-8")
    edges=[]
    for r in records:
        for target in r["targets"]: edges.append(f'    "{r["source"]}" -->|"{r["id"]}"| "{target}"')
    (out/"topology.mmd").write_text("flowchart LR\n"+"\n".join(edges)+"\n",encoding="utf-8")
    rows="".join(f"<tr data-search='{html.escape((r['id']+' '+r['name']+' '+r['source']+' '+' '.join(r['targets'])+' '+r['protocol']+' '+r['owner']).lower())}'><td><a href='interfaces/{html.escape(r['id'])}.html'>{html.escape(r['id'])}</a></td><td>{html.escape(r['name'])}</td><td>{html.escape(r['source'])}</td><td>{html.escape(', '.join(r['targets']))}</td><td>{html.escape(r['protocol'])}</td><td>{html.escape(r['criticality'])}</td><td>{html.escape(r['owner'])}</td></tr>" for r in records)
    page="""<!doctype html><meta charset='utf-8'><title>Interface catalog</title><style>body{font-family:system-ui;max-width:1200px;margin:40px auto;padding:0 20px}input{width:100%;padding:12px;margin:16px 0}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:8px;border-bottom:1px solid #ddd}</style><h1>Interface catalog</h1><p>Validated Git-native operational contracts.</p><input id='q' placeholder='Search interfaces, systems, protocols, owners'><table><thead><tr><th>ID</th><th>Name</th><th>Source</th><th>Targets</th><th>Protocol</th><th>Criticality</th><th>Owner</th></tr></thead><tbody>"""+rows+"</tbody></table><script>q.oninput=()=>{let v=q.value.toLowerCase();document.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.dataset.search.includes(v))}</script>"
    (out/"index.html").write_text(page,encoding="utf-8")
    return index
