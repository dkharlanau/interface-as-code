import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

from interface_as_code.controls import control_model
from interface_as_code.handover import build_handover, render_handover
from interface_as_code.loader import SpecLoadError, load_yaml
from interface_as_code.policies import check_spec
from interface_as_code.testplan import generate_test_plan

ROOT = Path(__file__).resolve().parents[1]


def cli(*args):
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'))
    return subprocess.run([sys.executable, '-m', 'interface_as_code.cli', 'handover', *map(str, args)], capture_output=True, text=True, env=env)


def example(tmp_path, name='sap-mdg-to-s4-customer'):
    dest = tmp_path / name
    shutil.copytree(ROOT / 'examples' / name, dest)
    return dest / 'interface.yaml'


@pytest.mark.parametrize('name', ['sap-mdg-to-s4-customer', 'rest-order-api', 'sap-event-mesh-order', 'sap-odata-product-api'])
def test_existing_example_models_are_reused_and_not_executed(name):
    # Resolve actual example names without creating protocol assumptions.
    path = ROOT / 'examples' / name / 'interface.yaml'
    if not path.exists():
        pytest.fail(f'Unknown example: {name}')
    before = path.read_bytes()
    spec = load_yaml(path)
    report = build_handover(path)
    assert report['source']['sha256'] == hashlib.sha256(before).hexdigest()
    assert report['declared_controls'] == control_model(spec)
    assert report['proposed_test_plan'] == generate_test_plan(spec)
    assert {q['code'] for q in report['readiness']['questions']} == {f.code for f in check_spec(spec)}
    assert report['acceptance'] == {'status': 'not_assessed', 'replay_authority': 'not_granted', 'test_execution': 'not_performed', 'evidence_verification': 'not_performed'}
    assert path.read_bytes() == before
    assert report == build_handover(path)


def test_gap_report_orders_actionable_questions_without_assigning_contacts():
    report = build_handover(ROOT / 'examples/governance/handover-gaps.yaml')
    questions = report['readiness']['questions']
    assert [q['code'] for q in questions[:2]] == ['owner.missing', 'support.route-missing']
    assert {'observability.business-key-missing', 'recoverability.replay-guidance-missing', 'reconciliation.comparison-missing'} <= {q['code'] for q in questions}
    assert all(q['path'].startswith('$.') and q['question'].endswith('?') and q['remediation'] for q in questions)
    assert report['declared_contacts'][0]['status'] == 'missing'
    assert report['declared_contacts'][2]['declared_value'] == 'SAP MDG Integration'
    assert report['declared_contacts'][2]['status'] == 'declared_not_confirmed'
    assert len(report['review_prompts']) == 3
    assert sum(report['readiness']['counts'].values()) == len(questions)


@pytest.mark.parametrize('threshold,expected', [('error',1),('warning',1),('info',1),('none',0)])
def test_public_cli_exit_does_not_replace_acceptance(threshold, expected):
    p = cli(ROOT / 'examples/governance/handover-gaps.yaml', '--format', 'json', '--fail-on', threshold)
    assert p.returncode == expected and not p.stderr
    report = json.loads(p.stdout)
    assert report['acceptance']['status'] == 'not_assessed'
    assert report['readiness']['counts']['error'] == 2


def test_clean_exit_has_no_acceptance_or_passed_tests():
    p = cli(ROOT / 'examples/rest-order-api/interface.yaml', '--format', 'json')
    assert p.returncode == 0 and not p.stderr
    r = json.loads(p.stdout)
    assert r['acceptance']['test_execution'] == 'not_performed'
    assert r['readiness']['counts']['info'] == 1
    assert all('status' not in x for x in r['proposed_test_plan']['cases'])


@pytest.mark.parametrize('content', ['', '[]', 'null', 'hello', 'interface: [', 'interface: {id: 12}'])
def test_invalid_contract_has_no_report_or_traceback(tmp_path, content):
    path = tmp_path / 'interface.yaml'; path.write_text(content)
    p = cli(path, '--format', 'json', '--fail-on', 'none')
    assert p.returncode == 2 and not p.stdout
    assert 'ERROR' in p.stderr and 'Traceback' not in p.stderr


def test_missing_file_is_input_error(tmp_path):
    p = cli(tmp_path / 'missing.yaml')
    assert p.returncode == 2 and not p.stdout and 'Traceback' not in p.stderr


def test_broken_local_reference_rejects_report(tmp_path):
    path = example(tmp_path)
    (path.parent / 'mapping.yaml').unlink()
    with pytest.raises(SpecLoadError, match='mapping-file-missing'):
        build_handover(path)


def test_sha_binds_exact_input_bytes_not_reformatted_data(tmp_path):
    path = example(tmp_path)
    first = build_handover(path)
    path.write_bytes(path.read_bytes() + b'\n# review note\n')
    second = build_handover(path)
    assert first['source']['sha256'] != second['source']['sha256']
    assert first['declared_controls'] == second['declared_controls']


def test_changed_target_does_not_inherit_evidence_approval(tmp_path):
    path = example(tmp_path)
    before = build_handover(path)
    spec = load_yaml(path)
    spec['interface']['target']['system'] = 'SYNTHETIC-NEW-TARGET'
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    after = build_handover(path)
    assert before['source']['sha256'] != after['source']['sha256']
    assert after['interface']['target']['system'] == 'SYNTHETIC-NEW-TARGET'
    assert after['acceptance']['evidence_verification'] == 'not_performed'
    assert after['acceptance']['status'] == 'not_assessed'
    assert after['declared_evidence'] == before['declared_evidence']
    assert 'SYNTHETIC-NEW-TARGET' in render_handover(after)
    assert 'Declared target:' in render_handover(after)


def test_load_once_binds_same_bytes_used_for_validation(tmp_path, monkeypatch):
    path = example(tmp_path)
    real = Path.read_bytes
    calls = []
    def read(p):
        if p == path:
            calls.append(p)
            assert len(calls) == 1
        return real(p)
    monkeypatch.setattr(Path, 'read_bytes', read)
    build_handover(path)
    assert len(calls) == 1


def test_markdown_neutralizes_source_markup_and_multiline_content(tmp_path):
    path = example(tmp_path)
    spec = load_yaml(path)
    spec['monitoring']['owner'] = '<img src=x onerror=alert(1)> [go](javascript:alert(2))\n# Approved'
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    text = render_handover(build_handover(path))
    assert '<img' not in text and '[go](javascript:' not in text
    assert '\n# Approved' not in text
    assert '&lt;img' in text
    assert 'Proposed checks, not executed tests' in text
    assert 'replay is not authorized' in text
    assert '## Declared contacts, not confirmed assignments' in text


def test_no_policy_overlay_or_output_option_silently_applied():
    for flag in ('--overlay', '--policy', '--output'):
        p = cli(ROOT / 'examples/rest-order-api/interface.yaml', flag, 'unexpected.yaml')
        assert p.returncode == 2 and not p.stdout


def test_declared_approval_reference_is_not_an_approval(tmp_path):
    path = example(tmp_path)
    spec = load_yaml(path)
    spec['evidence'] = [{'type': 'approval', 'ref': {'kind': 'evidence', 'uri': 'https://example.invalid/review'}, 'status': 'approved'}]
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    report = build_handover(path)
    assert report['declared_evidence'] == spec['evidence']
    assert report['acceptance']['status'] == 'not_assessed'
    assert report['acceptance']['evidence_verification'] == 'not_performed'
    assert report['acceptance']['replay_authority'] == 'not_granted'


def test_lone_surrogate_is_inert_text_not_a_cli_crash(tmp_path):
    path = example(tmp_path)
    spec = load_yaml(path); spec['monitoring']['owner'] = 'team\ud800'
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    p = cli(path)
    assert p.returncode == 0 and not p.stderr
    assert '\\ud800' in p.stdout and 'Support handover brief' in p.stdout
    p.stdout.encode('utf-8')


def test_normal_unicode_contacts_remain_readable(tmp_path):
    path = example(tmp_path)
    spec = load_yaml(path); spec['monitoring']['owner'] = 'München 支持'
    path.write_text(yaml.safe_dump(spec, sort_keys=False))
    p = cli(path)
    assert p.returncode == 0 and not p.stderr
    assert 'München 支持' in p.stdout
