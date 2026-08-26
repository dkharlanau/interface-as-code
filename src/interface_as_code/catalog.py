from __future__ import annotations
import html,json,subprocess
from collections import Counter
from pathlib import Path
from typing import Any
from .loader import load_yaml
from .validator import discover_specs,validate_spec
from .policies import check_spec
from .renderer import render_markdown

def _targets(spec):
    i=spec["interface"];return i.get("consumers") or [i["target"]]

def _git_context(root: str|Path) -> dict[str,str|None]:
    base=Path(root);cwd=base if base.is_dir() else base.parent
    rev=subprocess.run(["git","rev-parse","HEAD"],cwd=cwd,capture_output=True,text=True,check=False)
    top=subprocess.run(["git","rev-parse","--show-toplevel"],cwd=cwd,capture_output=True,text=True,check=False)
    remote=subprocess.run(["git","config","--get","remote.origin.url"],cwd=cwd,capture_output=True,text=True,check=False)
    revision=rev.stdout.strip() if rev.returncode==0 else None
    repo_root=top.stdout.strip() if top.returncode==0 else None
    raw=remote.stdout.strip() if remote.returncode==0 else None
    repo_url=None
    if raw:
        if raw.startswith("git@github.com:"):
            repo_url="https://github.com/"+raw.split(":",1)[1]
        elif raw.startswith("https://github.com/"):
            repo_url=raw
        if repo_url and repo_url.endswith(".git"):repo_url=repo_url[:-4]
    return {"revision":revision,"repo_root":repo_root,"repo_url":repo_url}

def _artifact_links(spec:dict[str,Any],spec_path:Path,ctx:dict[str,str|None])->list[tuple[str,str]]:
    links=[]
    revision,repo_root,repo_url=ctx.get("revision"),ctx.get("repo_root"),ctx.get("repo_url")
    def url_for(uri:str)->str:
        if uri.startswith(("http://","https://")):return uri
        if repo_root and repo_url and revision:
            target=(spec_path.parent/uri).resolve()
            try:rel=target.relative_to(Path(repo_root)).as_posix();return f"{repo_url}/blob/{revision}/{rel}"
            except ValueError:pass
        return uri
    for label,section in (("Contract","contract"),("Mapping","mapping"),("Reconciliation","reconciliation")):
        obj=spec.get(section,{})
        if isinstance(obj,dict):
            ref=obj.get("ref")
            if isinstance(ref,dict) and ref.get("uri"):links.append((f"{label} reference",url_for(str(ref["uri"]))))
            for key in ("schema_ref","file"):
                if obj.get(key):links.append((f"{label} {key}",url_for(str(obj[key]))))
    return links

def build_catalog(root:str|Path,output:str|Path,filters:dict[str,str]|None=None)->dict[str,Any]:
    filters={k:v for k,v in (filters or {}).items() if v}
    ctx=_git_context(root);revision=ctx.get("revision")
    out=Path(output);out.mkdir(parents=True,exist_ok=True);details=out/"interfaces";details.mkdir(exist_ok=True);records=[];invalid=[]
    for path in discover_specs(root):
        issues=validate_spec(path)
        if issues:invalid.append({"path":str(path),"issues":[str(x) for x in issues]});continue
        spec=load_yaml(path);i=spec["interface"];findings=check_spec(spec);record={"id":i["id"],"name":i["name"],"source":i["source"]["system"],"targets":[t["system"] for t in _targets(spec)],"mode":i["mode"],"protocol":spec["contract"]["format"],"criticality":i.get("criticality","") ,"lifecycle":i.get("lifecycle","") ,"owner":spec.get("monitoring",{}).get("owner","") ,"business_object":i.get("source",{}).get("object","") ,"findings":dict(Counter(x.severity for x in findings)),"path":str(path),"provenance":{"path":str(path),"revision":revision},"operations":{"ownership":spec.get("ownership",{}),"delivery":spec.get("delivery",{}),"retry":spec.get("retry",{}),"monitoring":spec.get("monitoring",{}),"reconciliation":spec.get("reconciliation",{}),"sla":spec.get("sla",{}),"security":spec.get("security",{})}}
        if filters.get("system") and filters["system"] not in [record["source"], *record["targets"]]:
            continue
        if filters.get("protocol") and record["protocol"] != filters["protocol"]:
            continue
        if filters.get("owner") and record["owner"] != filters["owner"]:
            continue
        if filters.get("criticality") and record["criticality"] != filters["criticality"]:
            continue
        if ctx.get("repo_root") and ctx.get("repo_url") and revision:
            try:
                rel=path.resolve().relative_to(Path(str(ctx["repo_root"]))).as_posix()
                record["provenance"]["source_url"]=f"{ctx['repo_url']}/blob/{revision}/{rel}"
                record["provenance"]["history_url"]=f"{ctx['repo_url']}/commits/{revision}/{rel}"
            except ValueError:pass
        records.append(record)
        md_name=f"{i['id']}.md"; (details/md_name).write_text(render_markdown(spec),encoding="utf-8")
        links=[f"<li><a href='{html.escape(md_name)}'>Generated Markdown documentation</a></li>"]
        if record["provenance"].get("source_url"):links.append(f"<li><a href='{html.escape(record['provenance']['source_url'])}'>Source specification</a></li>")
        if record["provenance"].get("history_url"):links.append(f"<li><a href='{html.escape(record['provenance']['history_url'])}'>Change history</a></li>")
        for label,url in _artifact_links(spec,path,ctx):links.append(f"<li><a href='{html.escape(url)}'>{html.escape(label)}</a></li>")
        body=f"<h1>{html.escape(i['name'])}</h1><p><code>{html.escape(i['id'])}</code></p><p>{html.escape(record['source'])} → {html.escape(', '.join(record['targets']))}</p><h2>Artifacts</h2><ul>{''.join(links)}</ul><h2>Readiness</h2><ul>"+"".join(f"<li><strong>{html.escape(x.severity)}</strong> {html.escape(x.code)} — {html.escape(x.message)}</li>" for x in findings)+"</ul>"
        (details/f"{i['id']}.html").write_text("<!doctype html><meta charset='utf-8'><title>"+html.escape(i['name'])+"</title>"+body,encoding="utf-8")
    summary={"total":len(records),"invalid":len(invalid),"filters":filters,"protocols":dict(Counter(x["protocol"] for x in records)),"criticality":dict(Counter(x["criticality"] for x in records)),"systems":len({x["source"] for x in records}|{t for x in records for t in x["targets"]})};index={"summary":summary,"interfaces":records,"invalid":invalid};(out/"index.json").write_text(json.dumps(index,indent=2),encoding="utf-8")
    edges=[f'    "{r["source"]}" -->|"{r["id"]}"| "{target}"' for r in records for target in r["targets"]];(out/"topology.mmd").write_text("flowchart LR\n"+"\n".join(edges)+"\n",encoding="utf-8")
    rows="".join(f"<tr data-search='{html.escape((r['id']+' '+r['name']+' '+r['source']+' '+' '.join(r['targets'])+' '+r['protocol']+' '+r['owner']).lower())}' data-protocol='{html.escape(r['protocol'])}' data-criticality='{html.escape(r['criticality'])}' data-lifecycle='{html.escape(r['lifecycle'])}' data-owner='{html.escape(r['owner'])}'><td><a href='interfaces/{html.escape(r['id'])}.html'>{html.escape(r['id'])}</a></td><td>{html.escape(r['name'])}</td><td>{html.escape(r['source'])}</td><td>{html.escape(', '.join(r['targets']))}</td><td>{html.escape(r['protocol'])}</td><td>{html.escape(r['criticality'])}</td><td>{html.escape(r['lifecycle'])}</td><td>{html.escape(r['owner'])}</td></tr>" for r in records)
    def options(field):return "<option value=''>All</option>"+"".join(f"<option>{html.escape(x)}</option>" for x in sorted({str(r[field]) for r in records if r[field]}))
    page="""<!doctype html><meta charset='utf-8'><title>Interface catalog</title><style>body{font-family:system-ui;max-width:1300px;margin:40px auto;padding:0 20px}input,select{padding:10px;margin:6px}input{min-width:320px}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:8px;border-bottom:1px solid #ddd}.filters{display:flex;flex-wrap:wrap}</style><h1>Interface catalog</h1><p>Validated Git-native operational contracts.</p><div class='filters'><input id='q' placeholder='Search ID, systems, protocol, owner'><select id='protocol'>"""+options("protocol")+"</select><select id='criticality'>"+options("criticality")+"</select><select id='lifecycle'>"+options("lifecycle")+"</select><select id='owner'>"+options("owner")+"</select></div><table><thead><tr><th>ID</th><th>Name</th><th>Source</th><th>Targets</th><th>Protocol</th><th>Criticality</th><th>Lifecycle</th><th>Owner</th></tr></thead><tbody>"+rows+"</tbody></table><script>function apply(){let text=q.value.toLowerCase();document.querySelectorAll('tbody tr').forEach(r=>{r.hidden=!(r.dataset.search.includes(text)&&(!protocol.value||r.dataset.protocol===protocol.value)&&(!criticality.value||r.dataset.criticality===criticality.value)&&(!lifecycle.value||r.dataset.lifecycle===lifecycle.value)&&(!owner.value||r.dataset.owner===owner.value))})}[q,protocol,criticality,lifecycle,owner].forEach(x=>x.oninput=apply)</script>";(out/"index.html").write_text(page,encoding="utf-8");return index
