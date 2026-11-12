"""Exercise the existing Mapping -> Interface handoff on synthetic examples.

Run from a trusted checkout with PyYAML/jsonschema installed. No network fetch,
SAP operation, mapping execution or acceptance grant occurs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import yaml

ROOT = Path(__file__).resolve().parents[1]


def rehearse(mapping_root: Path) -> dict:
    mapping_root = mapping_root.resolve()
    revision = subprocess.check_output(['git', '-C', str(mapping_root), 'rev-parse', 'HEAD'], text=True).strip()
    if subprocess.check_output(['git', '-C', str(mapping_root), 'status', '--porcelain'], text=True).strip():
        raise ValueError('Use a clean Mapping checkout so its revision describes the tested source.')
    calls = []
    def command(root, module, args, expected=0):
        env = dict(os.environ, PYTHONPATH=str(root / 'src'))
        env.pop('PYTHONHOME', None)
        p = subprocess.run([sys.executable, '-m', module, *map(str, args)], cwd=root,
                           env=env, capture_output=True, text=True, timeout=30)
        calls.append({'tool': module, 'command': str(args[0]), 'exit': p.returncode})
        if p.returncode != expected:
            raise AssertionError(f'{module} {args[0]}: expected {expected}, got {p.returncode}: {p.stderr} {p.stdout}')
        return p
    with tempfile.TemporaryDirectory(prefix='mapping-handover-') as temp:
        d = Path(temp)
        mapping = d / 'mapping.yaml'
        mapping.write_bytes((mapping_root / 'examples/customer-master.yaml').read_bytes())
        interface = mapping_root / 'examples/customer-interface.yaml'
        original = yaml.safe_load(interface.read_text())
        command(mapping_root, 'mapping_as_code.cli', ['validate', mapping])
        bound = d / 'bound.yaml'
        command(mapping_root, 'mapping_as_code.cli', ['bind-interface', interface, mapping,
            '--mapping-uri', 'mapping.yaml', '--revision', revision, '--output', bound])
        b = yaml.safe_load(bound.read_text())
        assert {k:v for k,v in b.items() if k != 'mapping'} == {k:v for k,v in original.items() if k != 'mapping'}
        canonical = hashlib.sha256(json.dumps(yaml.safe_load(mapping.read_text()),ensure_ascii=False,sort_keys=True,separators=(',', ':')).encode()).hexdigest()
        assert b['mapping']['ref']['sha256'] == canonical
        rejected = command(ROOT, 'interface_as_code.cli', ['validate', bound], expected=1)
        assert 'Checksum mismatch' in rejected.stdout
        raw_hash = hashlib.sha256(mapping.read_bytes()).hexdigest()
        assert raw_hash != canonical
        # Re-serialize the same synthetic document into Mapping's exact canonical
        # JSON representation. This artifact has equal raw and canonical hashes.
        artifact = d / 'mapping.json'
        artifact.write_bytes(json.dumps(yaml.safe_load(mapping.read_text()),ensure_ascii=False,sort_keys=True,separators=(',', ':')).encode())
        command(mapping_root, 'mapping_as_code.cli', ['validate', artifact])
        command(mapping_root, 'mapping_as_code.cli', ['bind-interface', interface, artifact,
            '--mapping-uri', 'mapping.json', '--revision', revision, '--output', bound])
        command(ROOT, 'interface_as_code.cli', ['validate', bound])
        report = json.loads(command(ROOT, 'interface_as_code.cli', ['handover', bound, '--format', 'json'], expected=1).stdout)
        assert report['acceptance']['status'] == 'not_assessed'
        assert report['acceptance']['replay_authority'] == 'not_granted'
        artifact.write_bytes(artifact.read_bytes() + b'\n')
        changed = command(ROOT, 'interface_as_code.cli', ['validate', bound], expected=1)
        assert 'Checksum mismatch' in changed.stdout
        bad = yaml.safe_load(interface.read_text())
        bad['interface']['target']['system'] = 'SYNTHETIC-OTHER'
        bad_path = d / 'mismatch.yaml'; bad_path.write_text(yaml.safe_dump(bad))
        denied = d / 'must-not-exist.yaml'
        p = command(mapping_root, 'mapping_as_code.cli', ['bind-interface', bad_path, mapping,
            '--mapping-uri', 'mapping.yaml', '--output', denied], expected=2)
        assert 'endpoint mismatch' in p.stderr and not denied.exists()
        return {'mapping_revision': revision, 'mapping_artifact': 'Derived canonical JSON from the pinned synthetic YAML; not a committed mapping.json file.',
                'consumer_source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / 'src' / 'interface_as_code').rglob('*')) if p.is_file() and p.suffix in ('.py', '.json')},
                'mapping_canonical_sha256': canonical,
                'commands': calls, 'operational_fields_preserved': True,
                'yaml_raw_sha256': raw_hash, 'ordinary_yaml_binding_rejected': True,
                'canonical_json_binding_validated': True, 'changed_bytes_rejected': True,
                'endpoint_mismatch_rejected': True, 'acceptance': 'not_assessed',
                'limits': 'Synthetic contract interoperability only; no runtime transformation or SAP proof.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mapping-root', required=True, type=Path)
    args = p.parse_args()
    print(json.dumps(rehearse(args.mapping_root), indent=2))
