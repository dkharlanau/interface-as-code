from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from .loader import SpecLoadError, load_yaml
from .renderer import render_markdown, render_mermaid
from .validator import discover_specs, validate_spec
from .scaffold import PROFILES, write_profile
from .importer import import_csv, load_mapping
from .policies import check_spec
from .diffing import semantic_diff
from .catalog import build_catalog

def _print_json(data): print(json.dumps(data,indent=2,default=str))
def _validate(path: str) -> int:
    specs=discover_specs(path)
    if not specs: print(f"ERROR: no interface.yaml files found under {path}",file=sys.stderr); return 2
    failed=0
    for spec in specs:
        try: issues=validate_spec(spec)
        except SpecLoadError as exc: print(f"ERROR {spec}: {exc}",file=sys.stderr); failed+=1; continue
        if issues:
            failed+=1; print(f"INVALID {spec}"); [print(f"- {x}") for x in issues]
        else: print(f"VALID {spec}")
    return 1 if failed else 0

def _render(path,output,format_name):
    issues=validate_spec(path)
    if issues:
        [print(f"- {x}",file=sys.stderr) for x in issues]; return 1
    spec=load_yaml(path); rendered=render_mermaid(spec) if format_name=="mermaid" else render_markdown(spec)
    if output:
        target=Path(output); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(rendered,encoding="utf-8"); print(f"WROTE {target}")
    else: print(rendered)
    return 0

def _init(args):
    iid=args.interface_id; name=args.name
    if not iid and sys.stdin.isatty(): iid=input("Interface ID: ").strip()
    if not name and sys.stdin.isatty(): name=input("Interface name: ").strip()
    iid=iid or "NEW-INTERFACE-01"; name=name or "New enterprise interface"
    path=write_profile(args.directory,args.profile,iid,name,args.source,args.target); print(f"WROTE {path}"); return 0

def _import_csv(args):
    report=import_csv(args.csv,args.output,load_mapping(args.columns),load_mapping(args.normalize_systems))
    print(f"GENERATED {len(report['generated'])} interfaces; {len(report['gaps'])} gaps -> {Path(args.output)/'import-report.json'}"); return 0

def _check(args):
    all_findings=[]; invalid=0
    for path in discover_specs(args.path):
        validation=validate_spec(path)
        if validation:
            invalid+=1; all_findings.append({"spec":str(path),"validation":[str(x) for x in validation],"findings":[]}); continue
        findings=check_spec(load_yaml(path)); all_findings.append({"spec":str(path),"validation":[],"findings":[x.to_dict() for x in findings]})
    if args.format=="json": _print_json(all_findings)
    else:
        for item in all_findings:
            print(f"## {item['spec']}")
            for err in item["validation"]: print(f"- ERROR validation: {err}")
            for x in item["findings"]: print(f"- {x['severity'].upper()} [{x['code']}] {x['message']} — {x['remediation']}")
    severities={"error":3,"warning":2,"info":1}; threshold=severities.get(args.fail_on,99)
    should_fail=bool(invalid) or any(severities.get(x["severity"],0)>=threshold for item in all_findings for x in item["findings"])
    return 1 if should_fail else 0

def _diff(args):
    changes=semantic_diff(load_yaml(args.old),load_yaml(args.new))
    if args.format=="json": _print_json([x.to_dict() for x in changes])
    elif not changes: print("no material changes")
    else:
        print("# Interface semantic diff")
        for x in changes: print(f"- **{x.severity}** `{x.path}`: `{x.old}` → `{x.new}` — {x.reason}")
    severities={"breaking":4,"high-risk":3,"review":2,"informational":1}; threshold=severities.get(args.fail_on,99)
    return 1 if any(severities[x.severity]>=threshold for x in changes) else 0

def _catalog(args):
    result=build_catalog(args.path,args.output); print(f"CATALOG {result['summary']['total']} valid / {result['summary']['invalid']} invalid -> {args.output}"); return 1 if result['summary']['invalid'] else 0

def build_parser():
    p=argparse.ArgumentParser(prog="interface-as-code",description="Operational contracts and governance for enterprise integrations."); sub=p.add_subparsers(dest="command",required=True)
    v=sub.add_parser("validate"); v.add_argument("path")
    r=sub.add_parser("render"); r.add_argument("spec"); r.add_argument("--format",choices=["markdown","mermaid"],default="markdown"); r.add_argument("-o","--output")
    init=sub.add_parser("init"); init.add_argument("directory"); init.add_argument("--profile",choices=PROFILES,default="rest-api"); init.add_argument("--id",dest="interface_id"); init.add_argument("--name"); init.add_argument("--source",default="SOURCE"); init.add_argument("--target",default="TARGET")
    imp=sub.add_parser("import-csv"); imp.add_argument("csv"); imp.add_argument("output"); imp.add_argument("--columns"); imp.add_argument("--normalize-systems")
    c=sub.add_parser("check"); c.add_argument("path"); c.add_argument("--format",choices=["markdown","json"],default="markdown"); c.add_argument("--fail-on",choices=["error","warning","info","none"],default="none")
    d=sub.add_parser("diff"); d.add_argument("old"); d.add_argument("new"); d.add_argument("--format",choices=["markdown","json"],default="markdown"); d.add_argument("--fail-on",choices=["breaking","high-risk","review","informational","none"],default="none")
    cat=sub.add_parser("catalog"); cat.add_argument("path"); cat.add_argument("-o","--output",default="generated/catalog")
    return p

def main():
    args=build_parser().parse_args()
    if args.command=="validate": raise SystemExit(_validate(args.path))
    if args.command=="render": raise SystemExit(_render(args.spec,args.output,args.format))
    if args.command=="init": raise SystemExit(_init(args))
    if args.command=="import-csv": raise SystemExit(_import_csv(args))
    if args.command=="check": raise SystemExit(_check(args))
    if args.command=="diff": raise SystemExit(_diff(args))
    if args.command=="catalog": raise SystemExit(_catalog(args))
if __name__=="__main__": main()
