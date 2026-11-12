import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

from interface_as_code.diffing import semantic_diff
from interface_as_code.handover import build_handover
from interface_as_code.handover_diff import build_handover_diff, handover_diff_gate, render_handover_diff
from interface_as_code.loader import SpecLoadError, load_yaml

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / 'examples/governance'


def pair(tmp_path):
    for n in ('before', 'after'):
        shutil.copytree(ROOT/'examples/sap-mdg-to-s4-customer',tmp_path/n)
    return tmp_path/'before/interface.yaml', tmp_path/'after/interface.yaml'


def cli(*args):
    return subprocess.run([sys.executable,'-m','interface_as_code.cli','handover-diff',*map(str,args)],env=dict(os.environ,PYTHONPATH=str(ROOT/'src')),capture_output=True,text=True)


def test_target_change_exposes_review_scope_without_transferring_approval():
    before=FIX/'handover-before.yaml';after=FIX/'handover-after.yaml'
    r=build_handover_diff(before,after)
    assert r['changes']==[c.to_dict() for c in semantic_diff(load_yaml(before),load_yaml(after))]
    assert r['change_counts']['breaking']==1 and r['change_counts']['review']==1
    assert {x['area'] for x in r['review_scope']}=={'contacts','recovery','reconciliation','test_intent'}
    assert all(x['paths'] and x['question'].endswith('?') for x in r['review_scope'])
    assert not r['acceptance']['previous_approval_transferred']
    assert r['acceptance']['status']=='not_assessed' and r['reference_content_comparison']=='not_performed'
    assert r['previous_handover']==build_handover(before)
    assert r['current_handover']==build_handover(after)
    assert r==build_handover_diff(before,after)
    assert handover_diff_gate(r,'breaking','error')['exit']==1


@pytest.mark.parametrize('change,readiness,exit_code', [('breaking','error',1),('high-risk','none',1),('review','none',1),('none','error',0),('none','info',1),('none','none',0)])
def test_cli_separates_change_and_readiness_thresholds(change,readiness,exit_code):
    p=cli(FIX/'handover-before.yaml',FIX/'handover-after.yaml','--format','json','--fail-on-change',change,'--fail-on',readiness)
    assert p.returncode==exit_code and not p.stderr
    r=json.loads(p.stdout)
    assert r['gate']['exit']==exit_code
    assert r['gate']['change_threshold']==change
    assert r['acceptance']['previous_approval_transferred'] is False


def test_current_readiness_error_blocks_even_when_change_gate_disabled(tmp_path):
    a,b=pair(tmp_path);s=load_yaml(b);s['monitoring']['owner']='   ';b.write_text(yaml.safe_dump(s,sort_keys=False))
    p=cli(a,b,'--fail-on-change','none','--format','json')
    assert p.returncode==1
    g=json.loads(p.stdout)['gate']
    assert g['change_findings_at_threshold']==0 and g['readiness_findings_at_threshold']==1


def test_old_readiness_errors_are_not_silently_counted_as_current_failures(tmp_path):
    a,b=pair(tmp_path);s=load_yaml(a);s['monitoring']['owner']='   ';a.write_text(yaml.safe_dump(s,sort_keys=False))
    r=build_handover_diff(a,b)
    assert r['previous_handover']['readiness']['counts']['error']==1
    assert r['current_handover']['readiness']['counts']['error']==0
    assert handover_diff_gate(r,'none','error')['exit']==0
    assert r['acceptance']['status']=='not_assessed'


def test_comment_only_change_is_not_reported_as_semantic_change(tmp_path):
    a,b=pair(tmp_path);b.write_bytes(b.read_bytes()+b'\n# synthetic comment\n')
    r=build_handover_diff(a,b)
    assert r['source_bytes_changed'] and not r['changes'] and not r['review_scope']
    assert r['previous_source']['sha256']!=r['current_source']['sha256']
    assert 'Referenced contents were not compared' in render_handover_diff(r)


def test_identical_contract_is_not_approval(tmp_path):
    a,b=pair(tmp_path);r=build_handover_diff(a,b)
    assert not r['source_bytes_changed'] and not r['changes']
    assert r['acceptance']['status']=='not_assessed'
    assert handover_diff_gate(r,'breaking','error')['exit']==0


def test_unchanged_reference_with_different_file_bytes_is_explicitly_uncompared(tmp_path):
    a,b=pair(tmp_path);(b.parent/'mapping.yaml').write_text('synthetic: changed\n')
    r=build_handover_diff(a,b)
    assert not r['changes'] and not r['source_bytes_changed']
    assert r['reference_content_comparison']=='not_performed'
    assert 'changed contents' in ' '.join(r['limits'])


def test_unrelated_identity_rejected_even_if_gates_disabled(tmp_path):
    a,b=pair(tmp_path);s=load_yaml(b);s['interface']['id']='OTHER-INTERFACE';b.write_text(yaml.safe_dump(s,sort_keys=False))
    p=cli(a,b,'--format','json','--fail-on','none','--fail-on-change','none')
    assert p.returncode==2 and not p.stdout and 'same interface.id' in p.stderr


@pytest.mark.parametrize('which', ['before','after'])
@pytest.mark.parametrize('content', ['interface: []','not: [valid','null'])
def test_invalid_side_cannot_emit_partial_report(tmp_path,which,content):
    a,b=pair(tmp_path);path=a if which=='before' else b;path.write_text(content)
    p=cli(a,b,'--format','json')
    assert p.returncode==2 and not p.stdout and 'Traceback' not in p.stderr


def test_missing_reference_fails_before_any_report(tmp_path):
    a,b=pair(tmp_path);(b.parent/'mapping.yaml').unlink()
    with pytest.raises(SpecLoadError,match='mapping-file-missing'):build_handover_diff(a,b)


def test_both_source_hashes_bind_bytes_without_reloading_or_mutating(tmp_path,monkeypatch):
    a,b=pair(tmp_path);before={p:p.read_bytes() for p in (a,b)};calls={a:0,b:0};real=Path.read_bytes
    def read(p):
        if p in calls:calls[p]+=1
        return real(p)
    monkeypatch.setattr(Path,'read_bytes',read)
    r=build_handover_diff(a,b)
    assert calls=={a:1,b:1}
    assert r['previous_source']['sha256']==hashlib.sha256(before[a]).hexdigest()
    assert r['current_source']['sha256']==hashlib.sha256(before[b]).hexdigest()
    assert all(real(p)==v for p,v in before.items())


def test_identical_approved_evidence_never_transfers_approval(tmp_path):
    a,b=pair(tmp_path)
    for path in (a,b):
        s=load_yaml(path);s['evidence']=[{'type':'approval','ref':{'kind':'evidence','uri':'https://example.invalid/review'},'status':'approved'}]
        if path==b:s['interface']['target']['system']='SYNTHETIC-OTHER'
        path.write_text(yaml.safe_dump(s,sort_keys=False))
    r=build_handover_diff(a,b)
    assert r['previous_handover']['declared_evidence']==r['current_handover']['declared_evidence']
    assert r['acceptance']['previous_approval_transferred'] is False
    assert r['acceptance']['evidence_verification']=='not_performed'


def test_markdown_keeps_untrusted_changed_values_inert(tmp_path):
    a,b=pair(tmp_path);s=load_yaml(b);s['monitoring']['owner']='team\ud800 <script>alert(1)</script> [link](javascript:x)\n# Approved'
    b.write_text(yaml.safe_dump(s,sort_keys=False));p=cli(a,b)
    assert p.returncode==0 and not p.stderr
    assert '<script>' not in p.stdout and '[link](javascript:' not in p.stdout and '\n# Approved' not in p.stdout
    assert '\\ud800' in p.stdout and 'Previous approval is not transferred' in p.stdout
