from pathlib import Path
import json, subprocess, sys, yaml
import pytest
from interface_as_code.standards import import_openapi, import_asyncapi
from interface_as_code.loader import dump_yaml, load_yaml
from interface_as_code.validator import validate_spec, schema_issues
from interface_as_code.controls import control_model
from interface_as_code.governance import apply_overlay, apply_policy_pack, load_overlay
from interface_as_code.policies import Finding
from interface_as_code.observability import requirements
from interface_as_code.testplan import generate_test_plan
from interface_as_code.adapters import backstage_entity, leanix_interface_export
from interface_as_code.sap import sap_summary
from interface_as_code.drift import compare_evidence
from interface_as_code.catalog_service import CatalogService
from interface_as_code.catalog import build_catalog
from interface_as_code.importer import import_csv
from interface_as_code.diffing import load_spec_source, semantic_diff
from interface_as_code.scaffold import PROFILES, write_profile
ROOT=Path(__file__).parents[1]

def test_openapi_import(tmp_path):
    contract=ROOT/'examples/rest-order-api/openapi.yaml';out=tmp_path/'openapi';spec,_=import_openapi(contract,interface_id='OPENAPI-001',source='Portal',target='OMS',output_dir=out);out.mkdir();dump_yaml(spec,out/'interface.yaml');assert validate_spec(out/'interface.yaml')==[] and spec['contract']['ref']['kind']=='openapi'

def test_asyncapi_import(tmp_path):
    contract=ROOT/'examples/sap-event-mesh-order/asyncapi.yaml';out=tmp_path/'async';spec,_=import_asyncapi(contract,interface_id='ASYNC-001',source='SAP-S4',target='OMS',output_dir=out);out.mkdir();dump_yaml(spec,out/'interface.yaml');assert validate_spec(out/'interface.yaml')==[] and spec['trigger']['event']=='order.created'

def test_controls_are_concrete():
    model=control_model(load_yaml(ROOT/'examples/sap-mdg-to-s4-customer/interface.yaml'));assert model['recovery']['idempotency_key']=='customer_id' and model['reconciliation']['source_of_truth']=='SAP-MDG'

def test_policy_pack_and_overlay():
    spec=load_yaml(ROOT/'examples/sap-mdg-to-s4-customer/interface.yaml');effective,prov=apply_overlay(spec,load_overlay(ROOT/'examples/governance/prod.overlay.yaml'));assert effective['sla']['recovery_target']=='30 minutes' and prov['sla.recovery_target']=='PROD'
    with pytest.raises(ValueError):apply_overlay(spec,{'set':{'contract.version':'2'}})
    assert apply_policy_pack([Finding('warning','x','$.x','m','r')],{'rules':{'x':{'severity':'error'}}})[0].severity=='error'

def test_observability_rest_vs_messaging():
    rest=requirements(load_yaml(ROOT/'examples/rest-order-api/interface.yaml'));msg=requirements(load_yaml(ROOT/'examples/sap-event-mesh-order/interface.yaml'));assert 'latency' in rest['required_signals'] and 'consumer lag/backlog' in msg['required_signals'];assert any('messaging' in x['family'].lower() and x['status']=='Development' for x in msg['semantic_conventions'])

def test_test_plan_derives_replay_and_security():
    ids={x['id'] for x in generate_test_plan(load_yaml(ROOT/'examples/sap-event-mesh-order/interface.yaml'))['cases']};assert {'duplicate-delivery','dead-letter','safe-replay','reconciliation'}<=ids

def test_adapters_preserve_stable_id():
    spec=load_yaml(ROOT/'examples/rest-order-api/interface.yaml');assert backstage_entity(spec)['metadata']['annotations']['interface-as-code/id']=='ORDER-API-01' and leanix_interface_export(spec)['externalId']=='ORDER-API-01'

def test_three_sap_scenarios_valid_and_profiled():
    for path in [ROOT/'examples/sap-mdg-to-s4-customer/interface.yaml',ROOT/'examples/sap-odata-product-api/interface.yaml',ROOT/'examples/sap-event-mesh-order/interface.yaml']:
        assert validate_spec(path)==[] and sap_summary(load_yaml(path))['technology']

def test_drift_distinguishes_match_drift_unavailable():
    spec=load_yaml(ROOT/'examples/rest-order-api/interface.yaml');ev={'observations':[{'path':'$.interface.lifecycle','value':'active','source':'catalog'},{'path':'$.contract.version','value':'old','source':'runtime'},{'path':'$.contract.format','status':'unavailable','source':'runtime'}]};assert [x.status for x in compare_evidence(spec,ev)]==['match','drift','unavailable']

def test_versioned_schema_and_conformance():
    package=json.loads((ROOT/'src/interface_as_code/schemas/interface.schema.json').read_text());published=json.loads((ROOT/'spec/v1.0/interface.schema.json').read_text());assert package==published;assert validate_spec(ROOT/'conformance/v1.0/valid/basic/interface.yaml')==[];assert schema_issues(load_yaml(ROOT/'conformance/v1.0/invalid/missing-monitoring.yaml'))

def test_catalog_service_is_read_only_search_surface(tmp_path):
    build_catalog(ROOT/'examples',tmp_path/'catalog');svc=CatalogService(tmp_path/'catalog');assert svc.search('SAP') and svc.get('ORDER-API-01')['protocol']=='REST'

def test_import_lineage(tmp_path):
    report=import_csv(ROOT/'tests/fixtures/inventory-50.csv',tmp_path/'out');assert report['lineage']['IMP-001']['fields']['source']['source_column']=='source'

def test_soap_and_minimal_scaffolds_validate(tmp_path):
    assert 'soap' in PROFILES;assert validate_spec(write_profile(tmp_path/'soap','soap','SOAP-001','SOAP example',minimal=True))==[]

def test_diff_git_ref_source(tmp_path,monkeypatch):
    repo=tmp_path/'repo';repo.mkdir();subprocess.run(['git','init','-q'],cwd=repo,check=True);subprocess.run(['git','config','user.email','x@example.com'],cwd=repo,check=True);subprocess.run(['git','config','user.name','x'],cwd=repo,check=True);d=repo/'one';d.mkdir();write_profile(d,'rest-api','GIT-001','Git example');subprocess.run(['git','add','.'],cwd=repo,check=True);subprocess.run(['git','commit','-qm','base'],cwd=repo,check=True);old=load_yaml(d/'interface.yaml');new=yaml.safe_load(yaml.safe_dump(old));new['interface']['lifecycle']='active';dump_yaml(new,d/'interface.yaml');monkeypatch.chdir(repo);assert semantic_diff(load_spec_source('HEAD:one/interface.yaml'),new)

def test_catalog_html_has_explicit_filters(tmp_path):
    build_catalog(ROOT/'examples',tmp_path/'catalog');text=(tmp_path/'catalog/index.html').read_text();assert "id='protocol'" in text and "id='criticality'" in text and "id='owner'" in text

def test_mcp_module_imports_without_optional_dependency():
    import interface_as_code.mcp_server as mod;assert callable(mod.create_server)

def test_sap_offline_metadata_import():
    from interface_as_code.sap import apply_offline_metadata
    updated,ignored=apply_offline_metadata(load_yaml(ROOT/'examples/sap-odata-product-api/interface.yaml'),{'iflow_id':'FLOW-1','technology':'Cloud Integration','unknown':'x'});assert updated['profiles']['sap']['iflow_id']=='FLOW-1' and ignored==['unknown']

def test_noop_migration_is_deterministic():
    from interface_as_code.versioning import migrate_spec
    spec=load_yaml(ROOT/'examples/rest-order-api/interface.yaml');migrated,notes=migrate_spec(spec,'1.0');assert migrated==spec and notes

def test_github_check_output(tmp_path):
    import os
    cmd=[sys.executable,'-m','interface_as_code.cli','check',str(ROOT/'examples/sap-event-mesh-order'),'--format','github','--fail-on','none'];env=dict(os.environ);env['PYTHONPATH']=str(ROOT/'src');result=subprocess.run(cmd,capture_output=True,text=True,env=env);assert result.returncode==0 and '::notice file=' in result.stdout

def test_leanix_inbound_is_comparison_not_overwrite():
    from interface_as_code.adapters import compare_leanix_snapshot
    diffs=compare_leanix_snapshot(load_yaml(ROOT/'examples/rest-order-api/interface.yaml'),{'externalId':'ORDER-API-01','provider':'WRONG'});assert diffs==[{'field':'provider','interface_as_code':'Commerce-Platform','leanix':'WRONG','status':'different'}]


def test_import_detects_inconsistent_system_spelling(tmp_path):
    csv=tmp_path/'systems.csv'
    csv.write_text('interface_id,name,source,target,protocol,owner,support_route,business_key\nSYS-001,One,SAP-S4,OMS,REST,Ops,Q,id1\nSYS-002,Two,SAP S4,WMS,REST,Ops,Q,id2\n',encoding='utf-8')
    report=import_csv(csv,tmp_path/'out')
    assert any(g['field']=='system_name_consistency' for g in report['gaps'])

def test_scoped_catalog_filters_topology(tmp_path):
    result=build_catalog(ROOT/'examples',tmp_path/'scoped',{'system':'SAP-S4'})
    assert result['summary']['filters']['system']=='SAP-S4'
    assert result['interfaces']
    assert all('SAP-S4' in [x['source'],*x['targets']] for x in result['interfaces'])
    topology=(tmp_path/'scoped/topology.mmd').read_text()
    assert 'SAP-S4' in topology
