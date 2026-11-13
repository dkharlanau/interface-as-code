from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

import pytest

from interface_as_code.catalog import build_catalog
from interface_as_code.catalog_service import CatalogService
from interface_as_code.handover import build_handover
from interface_as_code.scaffold import write_profile

ROOT = Path(__file__).resolve().parents[1]
GAPS = ROOT / 'examples/governance/handover-gaps.yaml'


def test_opt_in_reuses_handover_questions_and_exact_source(tmp_path):
    index = build_catalog(GAPS, tmp_path/'catalog', include_handover=True)
    record = index['interfaces'][0]
    expected = build_handover(GAPS)
    assert record['handover']['readiness'] == expected['readiness']
    assert record['handover']['declared_contacts'] == expected['declared_contacts']
    assert record['handover']['acceptance'] == expected['acceptance']
    assert record['handover']['readiness']['counts'] == {'error': 2, 'warning': 3, 'info': 1}
    digest = hashlib.sha256(GAPS.read_bytes()).hexdigest()
    assert record['provenance']['sha256'] == digest
    assert record['handover']['source']['sha256'] == digest
    assert 'proposed_test_plan' not in record['handover']
    assert 'declared_evidence' not in record['handover']


def test_default_catalog_remains_without_projection(tmp_path):
    index = build_catalog(GAPS, tmp_path/'catalog')
    assert 'handover' not in index['interfaces'][0]
    response = CatalogService(tmp_path/'catalog').handover(index['interfaces'][0]['id'])
    assert response['error'] == 'handover_not_in_catalog'
    assert 'absence is not a clean review' in response['next_step']


def test_query_reads_snapshot_not_live_sources(tmp_path, monkeypatch):
    source = write_profile(tmp_path/'contract', 'rest-api', 'SNAPSHOT', 'Snapshot', 'Portal', 'ERP')
    build_catalog(source, tmp_path/'catalog', include_handover=True)
    service = CatalogService(tmp_path/'catalog')
    expected = service.handover('SNAPSHOT')
    source.unlink()
    (tmp_path/'catalog/index.json').write_text('{}')
    def denied(*args, **kwargs):
        raise AssertionError('query must not read any file')
    monkeypatch.setattr(Path, 'read_bytes', denied)
    monkeypatch.setattr(Path, 'read_text', denied)
    assert service.handover('SNAPSHOT') == expected
    assert expected['catalog_snapshot']['freshness'] == 'not_checked'
    assert expected['handover']['acceptance']['replay_authority'] == 'not_granted'


def test_list_search_and_get_do_not_expand_context(tmp_path):
    build_catalog(GAPS, tmp_path/'catalog', include_handover=True)
    service = CatalogService(tmp_path/'catalog')
    assert all('handover' not in item for item in service.list())
    assert all('handover' not in item for item in service.search('SAP'))
    assert 'handover' not in service.get('SYNTHETIC-CUSTOMER-HANDOVER-GAPS')
    assert service.handover('missing')['error'] == 'not_found'


def test_invalid_spec_never_yields_handover(tmp_path):
    path=tmp_path/'interface.yaml';path.write_text('version: bad')
    index=build_catalog(path,tmp_path/'catalog',include_handover=True)
    assert index['summary']['invalid']==1 and index['summary']['total']==0
    assert CatalogService(tmp_path/'catalog').handover('anything')['error']=='not_found'


def test_opt_in_loads_exact_source_once(tmp_path, monkeypatch):
    original = Path.read_bytes
    calls = []
    def count(path):
        if path == GAPS:
            calls.append(path)
        return original(path)
    monkeypatch.setattr(Path,'read_bytes',count)
    build_catalog(GAPS,tmp_path/'catalog',include_handover=True)
    assert calls == [GAPS]


def test_committed_and_edited_provenance(tmp_path):
    repo=tmp_path/'repo';repo.mkdir()
    for args in (['init','-q'], ['config','user.name','Synthetic'], ['config','user.email','synthetic@example.invalid'],
                 ['remote','add','origin','https://github.com/example/synthetic.git']):
        subprocess.run(['git',*args],cwd=repo,check=True,capture_output=True)
    source=write_profile(repo/'contract','rest-api','COMMITTED','Committed','Portal','ERP')
    subprocess.run(['git','add','.'],cwd=repo,check=True)
    subprocess.run(['git','commit','-qm','Synthetic contract'],cwd=repo,check=True)
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    first=build_catalog(source,tmp_path/'first',include_handover=True)['interfaces'][0]
    assert first['provenance']['revision']==revision
    assert first['provenance']['source_state']=='committed'
    assert '/blob/'+revision+'/' in first['provenance']['source_url']
    source.write_text(source.read_text()+'\n# Uncommitted comment\n')
    edited=build_catalog(source,tmp_path/'edited',include_handover=True)['interfaces'][0]
    assert edited['provenance']['revision'] is None
    assert edited['provenance']['repository_revision']==revision
    assert edited['provenance']['source_state']=='modified_or_untracked'
    assert 'source_url' not in edited['provenance']
    assert edited['provenance']['sha256'] != first['provenance']['sha256']


def test_no_repository_has_hash_without_commit_claim(tmp_path):
    source=write_profile(tmp_path/'contract','rest-api','LOCAL','Local','Portal','ERP')
    record=build_catalog(source,tmp_path/'catalog',include_handover=True)['interfaces'][0]
    assert record['provenance']['source_state']=='no_repository'
    assert record['provenance']['revision'] is None
    assert record['provenance']['sha256']


def test_handover_never_grants_approval_when_no_findings(tmp_path, monkeypatch):
    import interface_as_code.handover as handover
    monkeypatch.setattr(handover,'check_spec',lambda spec: [])
    record=build_catalog(GAPS,tmp_path/'catalog',include_handover=True)['interfaces'][0]
    assert record['handover']['readiness']['counts']=={'error':0,'warning':0,'info':0}
    assert record['handover']['acceptance']=={'status':'not_assessed','replay_authority':'not_granted',
                                            'test_execution':'not_performed','evidence_verification':'not_performed'}


def test_mcp_registers_read_only_projection(tmp_path, monkeypatch):
    class FakeServer:
        def __init__(self,name): self.tools={}
        def tool(self):
            def register(fn): self.tools[fn.__name__]=fn;return fn
            return register
    module=types.ModuleType('mcp.server');module.MCPServer=FakeServer
    monkeypatch.setitem(sys.modules,'mcp.server',module)
    from interface_as_code.mcp_server import create_server
    build_catalog(GAPS,tmp_path/'catalog',include_handover=True)
    server=create_server(str(tmp_path/'catalog'))
    assert set(server.tools)=={'list_interfaces','search_interfaces','get_interface',
                              'get_interface_operations','get_interface_handover','get_catalog_status'}
    result=server.tools['get_interface_handover']('SYNTHETIC-CUSTOMER-HANDOVER-GAPS')
    assert result['handover']['acceptance']['status']=='not_assessed'
    assert server.tools['get_interface_handover']('../../etc/passwd')['error']=='not_found'


def test_cli_include_handover(tmp_path):
    result=subprocess.run([sys.executable,'-m','interface_as_code.cli','catalog',str(GAPS),
                           '-o',str(tmp_path/'catalog'),'--include-handover'],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert CatalogService(tmp_path/'catalog').handover('SYNTHETIC-CUSTOMER-HANDOVER-GAPS')['handover']


def test_100_interface_targeted_query(tmp_path):
    for i in range(100):
        write_profile(tmp_path/'contracts'/str(i),'rest-api',f'ERP-{i:03}',f'Synthetic {i}','Portal','ERP')
    index=build_catalog(tmp_path/'contracts',tmp_path/'catalog',include_handover=True)
    assert index['summary']['total']==100
    service=CatalogService(tmp_path/'catalog')
    result=service.handover('ERP-071')
    assert result['interface_id']=='ERP-071'
    assert 'interfaces' not in result and 'ERP-072' not in json.dumps(result)
    assert result['handover']['source']['path'].endswith('71/interface.yaml')


def test_duplicate_ids_never_choose_arbitrary_handover(tmp_path):
    catalog=tmp_path/'index.json'
    catalog.write_text(json.dumps({'interfaces':[{'id':'DUP','handover':{}},{'id':'DUP','handover':{}}]}))
    assert CatalogService(catalog).handover('DUP')['error']=='ambiguous_interface_id'


@pytest.mark.parametrize('accessor', ['handover', 'list', 'search', 'get', 'operations'])
def test_queries_cannot_mutate_retained_snapshot(tmp_path, accessor):
    build_catalog(GAPS, tmp_path/'catalog', include_handover=True)
    service=CatalogService(tmp_path/'catalog')
    iid='SYNTHETIC-CUSTOMER-HANDOVER-GAPS'
    before=service.handover(iid)
    if accessor == 'list':
        response=service.list()[0]
    elif accessor == 'search':
        response=service.search('SAP')[0]
    else:
        response=getattr(service, accessor)(iid)
    response['provenance']['sha256']='forged'
    if 'handover' in response:
        response['handover']['acceptance']['status']='accepted'
        response['handover']['readiness']['questions'].clear()
    assert service.handover(iid)==before
    assert service.status()['summary']['total']==1
    changed_status=service.status();changed_status['summary']['total']=999
    assert service.status()['summary']['total']==1
