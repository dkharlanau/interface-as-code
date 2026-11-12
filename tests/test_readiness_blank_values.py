"""Whitespace must not impersonate operational ownership or recovery detail."""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

from interface_as_code.loader import load_yaml
from interface_as_code.policies import _missing, check_spec
from interface_as_code.validator import validate_spec

ROOT = Path(__file__).resolve().parents[1]
BLANKS = [' ', '   ', '\t\n', '\u00a0' * 3, '\u2003' * 3]
CASES = [
    ('monitoring.owner','owner.missing','error'),
    ('ownership.technical','owner.technical-missing','warning'),
    ('ownership.business','owner.business-missing','warning'),
    ('ownership.support','owner.support-missing','error'),
    ('delivery.idempotency.key','delivery.idempotency-key-missing','error'),
    ('retry.dead_letter','recoverability.dead-letter-missing','warning'),
    ('retry.replay','recoverability.replay-guidance-missing','warning'),
    ('monitoring.business_key','observability.business-key-missing','warning'),
    ('reconciliation.comparison','reconciliation.comparison-missing','warning'),
    ('reconciliation.key','reconciliation.key-missing','error'),
    ('sla.recovery_target','sla.recovery-target-missing','warning'),
    ('security.authentication','security.auth-missing','error'),
    ('security.data_classification','security.classification-missing','warning'),
    ('monitoring.support_route','support.route-missing','error'),
]


def set_field(spec, path, value):
    target = spec
    parts = path.split('.')
    for key in parts[:-1]: target = target.setdefault(key,{})
    target[parts[-1]] = value


@pytest.mark.parametrize('blank', BLANKS)
@pytest.mark.parametrize('path,code,severity', CASES)
def test_existing_policy_treats_whitespace_as_missing(blank,path,code,severity):
    spec=load_yaml(ROOT/'examples/rest-order-api/interface.yaml')
    spec['interface']['mode']='async'
    spec['retry']['dead_letter']='Controlled synthetic error queue'
    spec['retry']['replay']='Review correction and duplicate-risk evidence before replay.'
    set_field(spec,path,blank);before=deepcopy(spec)
    matches=[f for f in check_spec(spec) if f.code==code]
    assert len(matches)==1
    assert matches[0].severity==severity and matches[0].path=='$.'+path
    assert matches[0].remediation
    assert spec==before


@pytest.mark.parametrize('value', ['Ops', ' Ops ', '0', 'Team TODO operations', 'Unknown origin team'])
def test_nonblank_values_are_not_trimmed_or_mistaken_for_placeholders(value):
    spec=load_yaml(ROOT/'examples/rest-order-api/interface.yaml');spec['monitoring']['owner']=value
    assert 'owner.missing' not in [f.code for f in check_spec(spec)]
    assert spec['monitoring']['owner']==value


@pytest.mark.parametrize('value', [None, '', 'TODO', ' todo ', 'tBd', ' UNASSIGNED ', 'UNKNOWN', 'TODO-SOURCE', 'TODO-TARGET'])
def test_existing_placeholder_semantics_remain_missing(value):
    assert _missing(value)


@pytest.mark.parametrize('value', [0, False, [], {}])
def test_missing_predicate_does_not_replace_schema_type_validation(value):
    assert not _missing(value)


def run_cli(spec, *arguments):
    env={**os.environ,'PYTHONPATH':str(ROOT/'src')}
    return subprocess.run([sys.executable,'-m','interface_as_code.cli','check',str(spec),*arguments],env=env,capture_output=True,text=True)


def test_public_gate_fails_after_schema_valid_whitespace_owner_and_route(tmp_path):
    shutil.copytree(ROOT/'examples/rest-order-api',tmp_path/'case')
    path=tmp_path/'case/interface.yaml';spec=load_yaml(path)
    spec['monitoring']['owner']=' \t ';spec['monitoring']['support_route']=' \t\u00a0 '
    path.write_text(yaml.safe_dump(spec,sort_keys=False))
    assert validate_spec(path)==[]  # Structure is intentionally distinct from readiness.
    before=path.read_bytes();result=run_cli(path,'--format','json','--fail-on','error')
    assert result.returncode==1 and not result.stderr
    findings=json.loads(result.stdout)[0]['findings'];codes={f['code'] for f in findings}
    assert {'owner.missing','support.route-missing'} <= codes
    assert path.read_bytes()==before
    informational=run_cli(path,'--format','json','--fail-on','none')
    assert informational.returncode==0
    assert json.loads(informational.stdout)==json.loads(result.stdout)


def test_github_annotations_and_markdown_keep_actionable_context(tmp_path):
    shutil.copytree(ROOT/'examples/rest-order-api',tmp_path/'case');path=tmp_path/'case/interface.yaml'
    spec=load_yaml(path);spec['monitoring']['owner']='   ';path.write_text(yaml.safe_dump(spec,sort_keys=False))
    github=run_cli(path,'--format','github','--fail-on','error')
    assert github.returncode==1 and '::error file=' in github.stdout and 'title=owner.missing' in github.stdout
    markdown=run_cli(path,'--format','markdown','--fail-on','error')
    assert markdown.returncode==1 and 'Assign the team accountable for failures.' in markdown.stdout
