from __future__ import annotations
import html,json
from collections import Counter
from pathlib import Path
from typing import Any
from .loader import load_yaml
from .validator import discover_specs,validate_spec
from .policies import check_spec

def _targets(spec):
    i=spec["interface"];return i.get("consumers") or [i["target"]]

def build_catalog(root:str|Path,output:str|Path)->dict[str,Any]:
    out=Path(output);out.mkdir(parents=True,exist_ok=True);details=out/"interfaces";details.mkdir(exist_ok=True);records=[];invalid=[]
    for path in discover_specs(root):
        issues=validate_spec(path)
        if issues:invalid.append({"path":str(path),"issues":[str(x) for x in issues]});continue
        spec=load_yaml(path);i=spec["interface"];findings=check_spec(spec);record={"id":i["id"],"name":i["name"],"source":i["source"]["system"],"targets":[t["system"] for t in _targets(spec)],"mode":i["mode"],"protocol":spec["contract"]["format"],"criticality":i.get("criticality","") ,"lifecycle":i.get("lifecycle","") ,"owner":spec.get("monitoring",{}).get("owner","") ,"business_object":i.get("source",{}).get("object","") ,"findings":dict(Counter(x.severity for x in findings)),"path":str(path)};records.append(record)
        body=f"<h1>{html.escape(i['name'])}</h1><p><code>{html.escape(i['id'])}</code></p><p>{html.escape(record['source'])} → {html.escape(', '.join(record['targets']))}</p><h2>Readiness</h2><ul>"+"".join(f"<li><strong>{html.escape(x.severity)}</strong> {html.escape(x.code)} — {html.escape(x.message)}</li>" for x in findings)+"</ul>"
        (details/f"{i['id']}.html").write_text("<!doctype html><meta charset='utf-8'><title>"+html.escape(i['name'])+"</title>"+body,encoding="utf-8")
    summary={"total":len(records),"invalid":len(invalid),"protocols":dict(Counter(x["protocol"] for x in records)),"criticality":dict(Counter(x["criticality"] for x in records)),"systems":len({x["source"] for x in records}|{t for x in records for t in x["targets"]})};index={"summary":summary,"interfaces":records,"invalid":invalid};(out/"index.json").write_text(json.dumps(index,indent=2),encoding="utf-8")
    edges=[f'    "{r["source"]}" -->|"{r["id"]}"| "{target}"' for r in records for target in r["targets"]];(out/"topology.mmd").write_text("flowchart LR\n"+"\n".join(edges)+"\n",encoding="utf-8")
    rows="".join(f"<tr data-search='{html.escape((r['id']+' '+r['name']+' '+r['source']+' '+' '.join(r['targets'])+' '+r['protocol']+' '+r['owner']).lower())}' data-protocol='{html.escape(r['protocol'])}' data-criticality='{html.escape(r['criticality'])}' data-lifecycle='{html.escape(r['lifecycle'])}' data-owner='{html.escape(r['owner'])}'><td><a href='interfaces/{html.escape(r['id'])}.html'>{html.escape(r['id'])}</a></td><td>{html.escape(r['name'])}</td><td>{html.escape(r['source'])}</td><td>{html.escape(', '.join(r['targets']))}</td><td>{html.escape(r['protocol'])}</td><td>{html.escape(r['criticality'])}</td><td>{html.escape(r['lifecycle'])}</td><td>{html.escape(r['owner'])}</td></tr>" for r in records)
    def options(field):return "<option value=''>All</option>"+"".join(f"<option>{html.escape(x)}</option>" for x in sorted({str(r[field]) for r in records if r[field]}))
    page="""<!doctype html><meta charset='utf-8'><title>Interface catalog</title><style>body{font-family:system-ui;max-width:1300px;margin:40px auto;padding:0 20px}input,select{padding:10px;margin:6px}input{min-width:320px}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:8px;border-bottom:1px solid #ddd}.filters{display:flex;flex-wrap:wrap}</style><h1>Interface catalog</h1><p>Validated Git-native operational contracts.</p><div class='filters'><input id='q' placeholder='Search ID, systems, protocol, owner'><select id='protocol'>"""+options("protocol")+"</select><select id='criticality'>"+options("criticality")+"</select><select id='lifecycle'>"+options("lifecycle")+"</select><select id='owner'>"+options("owner")+"</select></div><table><thead><tr><th>ID</th><th>Name</th><th>Source</th><th>Targets</th><th>Protocol</th><th>Criticality</th><th>Lifecycle</th><th>Owner</th></tr></thead><tbody>"+rows+"</tbody></table><script>function apply(){let text=q.value.toLowerCase();document.querySelectorAll('tbody tr').forEach(r=>{r.hidden=!(r.dataset.search.includes(text)&&(!protocol.value||r.dataset.protocol===protocol.value)&&(!criticality.value||r.dataset.criticality===criticality.value)&&(!lifecycle.value||r.dataset.lifecycle===lifecycle.value)&&(!owner.value||r.dataset.owner===owner.value))})}[q,protocol,criticality,lifecycle,owner].forEach(x=>x.oninput=apply)</script>";(out/"index.html").write_text(page,encoding="utf-8");return index
