from pathlib import Path
import yaml
from interface_as_code.validator import semantic_issues, validate_spec
from interface_as_code.resolver import resolve_reference, ReferenceError
from interface_as_code.scaffold import PROFILES, write_profile
from interface_as_code.importer import import_csv
from interface_as_code.policies import check_spec
from interface_as_code.diffing import semantic_diff, classify
from interface_as_code.catalog import build_catalog
ROOT=Path(__file__).parents[1]

def test_examples_valid():
    assert validate_spec(ROOT/'examples/sap-mdg-to-s4-customer/interface.yaml')==[]
    assert validate_spec(ROOT/'examples/rest-order-api/interface.yaml')==[]

def test_at_least_once_requires_idempotency():
    spec={"delivery":{"guarantee":"at-least-once","idempotency":{"required":False}},"monitoring":{"owner":"Ops"},"reconciliation":{"key":"id"}}
    assert "at-least-once-idempotency-required" in {x.code for x in semantic_issues(spec)}

def test_reference_checksum(tmp_path):
    p=tmp_path/'a.txt'; p.write_text('x')
    import hashlib
    ref={"kind":"custom","uri":"a.txt","sha256":hashlib.sha256(b'x').hexdigest()}
    assert resolve_reference(ref,tmp_path).verified
    ref['sha256']='0'*64
    try: resolve_reference(ref,tmp_path); assert False
    except ReferenceError: pass

def test_all_scaffold_profiles_validate(tmp_path):
    for n,profile in enumerate(PROFILES):
        path=write_profile(tmp_path/profile,profile,f"TEST-{n+1:02d}",f"Test {profile}")
        assert validate_spec(path)==[]

def test_csv_import_and_gaps(tmp_path):
    csv=tmp_path/'inventory.csv'; csv.write_text('interface_id,name,source,target,protocol,owner,support_route,business_key\nA-001,A,S1,S2,REST,Ops,Queue,id\nB-001,B,S2,S3,IDoc,,,\n',encoding='utf-8')
    report=import_csv(csv,tmp_path/'out')
    assert len(report['generated'])==2 and report['gaps']
    assert validate_spec(tmp_path/'out/a-001/interface.yaml')==[]
    assert validate_spec(tmp_path/'out/b-001/interface.yaml')==[]

def test_policy_engine_has_high_signal_findings():
    spec=yaml.safe_load((ROOT/'examples/sap-mdg-to-s4-customer/interface.yaml').read_text())
    assert not any(x.severity=='error' for x in check_spec(spec))
    spec['delivery']['guarantee']='best-effort'
    assert 'delivery.best-effort-critical' in {x.code for x in check_spec(spec)}

def test_catalog_build(tmp_path):
    result=build_catalog(ROOT/'examples',tmp_path/'catalog')
    assert result['summary']['total']==2
    assert (tmp_path/'catalog/index.html').exists() and (tmp_path/'catalog/topology.mmd').exists()

CASES=[('$.interface.source.system','breaking'),('$.interface.target.system','breaking'),('$.interface.consumers','breaking'),('$.contract.format','breaking'),('$.contract.message_type','breaking'),('$.contract.basic_type','breaking'),('$.contract.schema_ref','breaking'),('$.contract.ref.uri','breaking'),('$.reconciliation.key','breaking'),('$.delivery.guarantee','high-risk'),('$.delivery.idempotency.required','high-risk'),('$.delivery.ordering','high-risk'),('$.retry.strategy','high-risk'),('$.retry.max_attempts','high-risk'),('$.retry.dead_letter','high-risk'),('$.reconciliation.source_of_truth','high-risk'),('$.sla.recovery_target','high-risk'),('$.security.authentication','high-risk'),('$.ownership.business','review'),('$.ownership.technical','review'),('$.ownership.support','review'),('$.monitoring.owner','review'),('$.monitoring.support_route','review'),('$.interface.lifecycle','review'),('$.route.middleware','review'),('$.monitoring.signals','informational'),('$.interface.description','informational'),('$.interface.tags','informational'),('$.tests','informational'),('$.evidence','informational')]

def test_change_classification_matrix():
    assert len(CASES)>=30
    for path,severity in CASES: assert classify(path,'a','b')[0]==severity

def test_semantic_diff():
    a=yaml.safe_load((ROOT/'examples/rest-order-api/interface.yaml').read_text()); b=yaml.safe_load(yaml.safe_dump(a)); b['reconciliation']['key']='new_id'
    changes=semantic_diff(a,b)
    assert any(x.path=='$.reconciliation.key' and x.severity=='breaking' for x in changes)

def test_csv_import_50_fixture(tmp_path):
    report=import_csv(ROOT/'tests/fixtures/inventory-50.csv',tmp_path/'imported')
    assert len(report['generated'])==50
    assert all(validate_spec(p)==[] for p in map(Path,report['generated']))

def test_catalog_100_specs(tmp_path):
    portfolio=tmp_path/'portfolio'
    for n in range(100):
        write_profile(portfolio/f'i{n:03d}','rest-api',f'SCALE-{n:03d}',f'Scale interface {n:03d}',f'SYS-{n%10}',f'SYS-{(n+1)%10}')
    result=build_catalog(portfolio,tmp_path/'catalog100')
    assert result['summary']['total']==100

def test_reference_landscape_inventory_30(tmp_path):
    report=import_csv(ROOT/'examples/reference-landscape/inventory.csv',tmp_path/'landscape')
    assert len(report['generated'])==30
    result=build_catalog(tmp_path/'landscape',tmp_path/'landscape-catalog')
    assert result['summary']['total']==30
