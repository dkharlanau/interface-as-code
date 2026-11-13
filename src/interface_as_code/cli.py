from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import yaml

from .loader import SpecLoadError, dump_yaml, load_yaml
from .renderer import render_markdown, render_mermaid
from .validator import discover_specs, validate_spec
from .scaffold import PROFILES, write_profile
from .importer import import_csv, load_mapping
from .policies import check_spec
from .governance import apply_overlay, apply_policy_pack, load_overlay, load_policy_pack
from .diffing import semantic_diff, load_spec_source
from .catalog import build_catalog
from .standards import import_openapi, import_asyncapi, imported_metadata
from .controls import render_controls
from .observability import render as render_observability
from .testplan import render as render_test_plan
from .adapters import render_adapter
from .sap import apply_offline_metadata, load_offline_metadata, render_sap_summary
from .drift import build_drift_report, load_evidence
from .versioning import SUPPORTED_SPEC_VERSIONS, migrate_spec
from .handover import build_handover, render_handover
from .handover_diff import build_handover_diff, handover_diff_gate, render_handover_diff


def _print_json(data): print(json.dumps(data,indent=2,default=str))
def _write_or_print(text, output=None):
    if output:
        target=Path(output);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text,encoding="utf-8");print(f"WROTE {target}")
    else: print(text,end="" if text.endswith("\n") else "\n")
def _gh_escape(value:str)->str:return value.replace('%','%25').replace('\r','%0D').replace('\n','%0A')

def _validate(path:str)->int:
    specs=discover_specs(path)
    if not specs:print(f"ERROR: no interface.yaml files found under {path}",file=sys.stderr);return 2
    failed=0
    for spec in specs:
        try:issues=validate_spec(spec)
        except SpecLoadError as exc:print(f"ERROR {spec}: {exc}",file=sys.stderr);failed+=1;continue
        if issues:failed+=1;print(f"INVALID {spec}");[print(f"- {x}") for x in issues]
        else:print(f"VALID {spec}")
    return 1 if failed else 0

def _render(path,output,format_name):
    issues=validate_spec(path)
    if issues:[print(f"- {x}",file=sys.stderr) for x in issues];return 1
    spec=load_yaml(path);_write_or_print(render_mermaid(spec) if format_name=="mermaid" else render_markdown(spec),output);return 0

def _init(args):
    iid=args.interface_id;name=args.name
    if not iid and sys.stdin.isatty():iid=input("Interface ID: ").strip()
    if not name and sys.stdin.isatty():name=input("Interface name: ").strip()
    iid=iid or "NEW-INTERFACE-01";name=name or "New enterprise interface"
    path=write_profile(args.directory,args.profile,iid,name,args.source,args.target,args.minimal);print(f"WROTE {path}");return 0

def _import_csv(args):
    report=import_csv(args.csv,args.output,load_mapping(args.columns),load_mapping(args.normalize_systems));print(f"GENERATED {len(report['generated'])} interfaces; {len(report['gaps'])} gaps -> {Path(args.output)/'import-report.json'}");return 0

def _check(args):
    specs = discover_specs(args.path)
    if not specs:
        print(f"ERROR: no interface.yaml files found under {args.path}", file=sys.stderr)
        return 2
    try:
        pack = load_policy_pack(args.policy) if args.policy else None
    except ValueError as exc:
        print(f"ERROR: invalid policy pack: {exc}", file=sys.stderr)
        return 2
    all_findings=[];invalid=0;overlay=load_overlay(args.overlay) if args.overlay else None
    for path in specs:
        validation=validate_spec(path)
        if validation:invalid+=1;all_findings.append({"spec":str(path),"validation":[str(x) for x in validation],"findings":[]});continue
        spec=load_yaml(path)
        if overlay:spec,_=apply_overlay(spec,overlay)
        findings=check_spec(spec)
        if pack:findings=apply_policy_pack(findings,pack)
        all_findings.append({"spec":str(path),"validation":[],"findings":[x.to_dict() for x in findings]})
    if args.format=="json":_print_json(all_findings)
    elif args.format=="github":
        for item in all_findings:
            file=_gh_escape(item['spec'])
            for err in item['validation']:print(f"::error file={file},title=Interface validation::{_gh_escape(err)}")
            for x in item['findings']:
                level='error' if x['severity']=='error' else 'warning' if x['severity']=='warning' else 'notice'
                print(f"::{level} file={file},title={_gh_escape(x['code'])}::{_gh_escape(x['message']+' '+x['remediation'])}")
    else:
        for item in all_findings:
            print(f"## {item['spec']}")
            for err in item["validation"]:print(f"- ERROR validation: {err}")
            for x in item["findings"]:print(f"- {x['severity'].upper()} [{x['code']}] {x['message']} — {x['remediation']}")
    ranks={"error":3,"warning":2,"info":1};threshold=ranks.get(args.fail_on,99);return 1 if invalid or any(ranks.get(x["severity"],0)>=threshold for item in all_findings for x in item["findings"]) else 0

def _diff(args):
    changes=semantic_diff(load_spec_source(args.old),load_spec_source(args.new))
    if args.format=="json":_print_json([x.to_dict() for x in changes])
    elif not changes:print("no material changes")
    else:
        print("# Interface semantic diff")
        for x in changes:print(f"- **{x.severity}** `{x.path}`: `{x.old}` → `{x.new}` — {x.reason}")
    ranks={"breaking":4,"high-risk":3,"review":2,"informational":1};threshold=ranks.get(args.fail_on,99);return 1 if any(ranks[x.severity]>=threshold for x in changes) else 0

def _catalog(args):
    filters={"system":args.system,"protocol":args.protocol,"owner":args.owner,"criticality":args.criticality}
    result=build_catalog(args.path,args.output,filters,include_handover=args.include_handover);print(f"CATALOG {result['summary']['total']} valid / {result['summary']['invalid']} invalid -> {args.output}");return 1 if result['summary']['invalid'] else 0

def _standard(args,kind):
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True);fn=import_openapi if kind=="openapi" else import_asyncapi;spec,warnings=fn(args.contract,interface_id=args.interface_id,source=args.source,target=args.target,output_dir=out);path=out/"interface.yaml";previous=load_yaml(path) if path.exists() and args.force else None
    if path.exists() and not args.force:print(f"ERROR: {path} exists; use --force",file=sys.stderr);return 2
    dump_yaml(spec,path);print(f"WROTE {path}");[print(f"WARNING: {x}") for x in warnings]
    if previous:print(f"REIMPORT metadata changes: {len(semantic_diff({'metadata':imported_metadata(previous)},{'metadata':imported_metadata(spec)}))}")
    return 0

def _generate(args,kind):
    issues=validate_spec(args.spec)
    if issues:[print(f"- {x}",file=sys.stderr) for x in issues];return 1
    spec=load_yaml(args.spec)
    if args.overlay:spec,_=apply_overlay(spec,load_overlay(args.overlay))
    if kind=="controls":text=render_controls(spec,args.format)
    elif kind=="observability":text=render_observability(spec,args.format)
    elif kind=="test-plan":text=render_test_plan(spec,args.format)
    elif kind=="sap":text=render_sap_summary(spec,args.format)
    else:raise ValueError(kind)
    _write_or_print(text,args.output);return 0

def _adapter(args):
    issues=validate_spec(args.spec)
    if issues:[print(f"- {x}",file=sys.stderr) for x in issues];return 1
    _write_or_print(render_adapter(load_yaml(args.spec),args.adapter),args.output);return 0

def _explain(args):
    spec=load_yaml(args.spec);overlay=load_overlay(args.overlay);effective,provenance=apply_overlay(spec,overlay);data={"environment":overlay.get("environment"),"provenance":provenance,"effective":effective}
    if args.format=="json":_print_json(data)
    else:_write_or_print("# Effective Interface as Code overlay\n\n"+"\n".join(f"- `{p}` ← **{src}**" for p,src in provenance.items())+"\n\n```yaml\n"+yaml.safe_dump(effective,sort_keys=False)+"```\n",args.output)
    return 0

def _drift(args):
    try:
        issues = validate_spec(args.spec)
        if issues:
            print("ERROR: invalid interface contract: " + "; ".join(map(str, issues)), file=sys.stderr)
            return 2
        report = build_drift_report(
            load_yaml(args.spec), load_evidence(args.evidence),
            stale_after_days=args.stale_after_days, evaluated_at=args.evaluated_at,
        )
    except (ValueError, OSError, yaml.YAMLError, OverflowError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.format == "report-json":
        _print_json(report)
    elif args.format == "json":
        _print_json(report["findings"])
    else:
        print(f"Evaluation: {report['evaluated_at']} | freshness limit: {args.stale_after_days} days | {report['outcome'].upper()}")
        for x in report["findings"]:
            print(f"- {x['status'].upper()} `{x['path']}` declared=`{x['declared']}` observed=`{x['observed']}` source={x['source']} — {x['message']}")
    if args.require_complete and not report["complete"]:
        return 2
    return 1 if (report["counts"].get("drift") or report["counts"].get("conflict")) and args.fail_on_drift else 0

def _handover(args):
    try:
        report = build_handover(args.spec)
    except (ValueError, OSError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        _print_json(report)
    else:
        print(render_handover(report), end="")
    ranks = {"error": 3, "warning": 2, "info": 1}
    threshold = ranks.get(args.fail_on, 99)
    return 1 if any(ranks[q["severity"]] >= threshold for q in report["readiness"]["questions"]) else 0


def _handover_diff(args):
    try:
        report = build_handover_diff(args.previous, args.current)
    except (ValueError, OSError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    report['gate'] = handover_diff_gate(report, args.fail_on_change, args.fail_on)
    if args.format == 'json':
        _print_json(report)
    else:
        print(render_handover_diff(report), end='')
    return report['gate']['exit']


def _sap_import(args):
    spec=load_yaml(args.spec);updated,ignored=apply_offline_metadata(spec,load_offline_metadata(args.metadata));dump_yaml(updated,args.output);print(f"WROTE {args.output}")
    if ignored:print("IGNORED unsupported SAP metadata keys: "+", ".join(ignored))
    return 0

def _migrate(args):
    spec=load_yaml(args.spec);updated,notes=migrate_spec(spec,args.to);target=args.output or args.spec
    if Path(target).resolve()==Path(args.spec).resolve() and not args.in_place:print("ERROR: use --in-place to replace the source or provide -o",file=sys.stderr);return 2
    dump_yaml(updated,target);[print(x) for x in notes];return 0

def build_parser():
    p=argparse.ArgumentParser(prog="interface-as-code",description="Operational contracts and governance for enterprise integrations.");sub=p.add_subparsers(dest="command",required=True)
    v=sub.add_parser("validate");v.add_argument("path")
    r=sub.add_parser("render");r.add_argument("spec");r.add_argument("--format",choices=["markdown","mermaid"],default="markdown");r.add_argument("-o","--output")
    init=sub.add_parser("init");init.add_argument("directory");init.add_argument("--profile",choices=PROFILES,default="rest-api");init.add_argument("--id",dest="interface_id");init.add_argument("--name");init.add_argument("--source",default="SOURCE");init.add_argument("--target",default="TARGET");init.add_argument("--minimal",action="store_true")
    imp=sub.add_parser("import-csv");imp.add_argument("csv");imp.add_argument("output");imp.add_argument("--columns");imp.add_argument("--normalize-systems")
    for command in ("import-openapi","import-asyncapi"):
        s=sub.add_parser(command);s.add_argument("contract");s.add_argument("output");s.add_argument("--id",dest="interface_id",required=True);s.add_argument("--source",required=True);s.add_argument("--target",required=True);s.add_argument("--force",action="store_true")
    c=sub.add_parser("check");c.add_argument("path");c.add_argument("--format",choices=["markdown","json","github"],default="markdown");c.add_argument("--fail-on",choices=["error","warning","info","none"],default="none");c.add_argument("--policy");c.add_argument("--overlay")
    d=sub.add_parser("diff");d.add_argument("old",help="File or REV:path/to/interface.yaml");d.add_argument("new",help="File or REV:path/to/interface.yaml");d.add_argument("--format",choices=["markdown","json"],default="markdown");d.add_argument("--fail-on",choices=["breaking","high-risk","review","informational","none"],default="none")
    cat=sub.add_parser("catalog");cat.add_argument("path");cat.add_argument("-o","--output",default="generated/catalog");cat.add_argument("--system");cat.add_argument("--protocol");cat.add_argument("--owner");cat.add_argument("--criticality",choices=["low","medium","high","critical"]);cat.add_argument("--include-handover",action="store_true",help="Include declaration-based support questions for read-only agent queries")
    for command in ("controls","observability","test-plan","sap-summary"):
        g=sub.add_parser(command);g.add_argument("spec");g.add_argument("--format",choices=["markdown","yaml"],default="markdown");g.add_argument("-o","--output");g.add_argument("--overlay")
    h=sub.add_parser("handover", help="Read-only support brief; not acceptance or replay authority");h.add_argument("spec");h.add_argument("--format",choices=["markdown","json"],default="markdown");h.add_argument("--fail-on",choices=["error","warning","info","none"],default="error")
    hd=sub.add_parser("handover-diff",help="Compare two declared support handovers without transferring approval");hd.add_argument("previous");hd.add_argument("current");hd.add_argument("--format",choices=["markdown","json"],default="markdown");hd.add_argument("--fail-on-change",choices=["breaking","high-risk","review","informational","none"],default="breaking");hd.add_argument("--fail-on",choices=["error","warning","info","none"],default="error")
    a=sub.add_parser("export");a.add_argument("adapter",choices=["backstage","leanix"]);a.add_argument("spec");a.add_argument("-o","--output")
    e=sub.add_parser("explain");e.add_argument("spec");e.add_argument("--overlay",required=True);e.add_argument("--format",choices=["markdown","json"],default="markdown");e.add_argument("-o","--output")
    dr=sub.add_parser("drift");dr.add_argument("spec");dr.add_argument("evidence");dr.add_argument("--format",choices=["markdown","json","report-json"],default="markdown");dr.add_argument("--stale-after-days",type=int);dr.add_argument("--fail-on-drift",action="store_true");dr.add_argument("--evaluated-at",help="Fixed ISO 8601 evaluation time with Z or UTC offset");dr.add_argument("--require-complete",action="store_true",help="Exit 2 for unresolved or empty evidence")
    si=sub.add_parser("sap-import-metadata");si.add_argument("spec");si.add_argument("metadata");si.add_argument("-o","--output",required=True)
    mig=sub.add_parser("migrate");mig.add_argument("spec");mig.add_argument("--to",choices=SUPPORTED_SPEC_VERSIONS,required=True);mig.add_argument("-o","--output");mig.add_argument("--in-place",action="store_true")
    return p

def main():
    args=build_parser().parse_args()
    if args.command=="validate":raise SystemExit(_validate(args.path))
    if args.command=="render":raise SystemExit(_render(args.spec,args.output,args.format))
    if args.command=="init":raise SystemExit(_init(args))
    if args.command=="import-csv":raise SystemExit(_import_csv(args))
    if args.command=="import-openapi":raise SystemExit(_standard(args,"openapi"))
    if args.command=="import-asyncapi":raise SystemExit(_standard(args,"asyncapi"))
    if args.command=="check":raise SystemExit(_check(args))
    if args.command=="diff":raise SystemExit(_diff(args))
    if args.command=="catalog":raise SystemExit(_catalog(args))
    if args.command in {"controls","observability","test-plan","sap-summary"}:raise SystemExit(_generate(args,"sap" if args.command=="sap-summary" else args.command))
    if args.command=="export":raise SystemExit(_adapter(args))
    if args.command=="explain":raise SystemExit(_explain(args))
    if args.command=="drift":raise SystemExit(_drift(args))
    if args.command=="handover":raise SystemExit(_handover(args))
    if args.command=="handover-diff":raise SystemExit(_handover_diff(args))
    if args.command=="sap-import-metadata":raise SystemExit(_sap_import(args))
    if args.command=="migrate":raise SystemExit(_migrate(args))
if __name__=="__main__":main()
