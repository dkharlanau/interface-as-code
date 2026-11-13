"""Local artifact problems become validation findings, not successful references."""
import hashlib
import os
from pathlib import Path

import pytest

from interface_as_code.resolver import ReferenceError, resolve_reference
from interface_as_code.validator import semantic_issues


@pytest.mark.parametrize('checksum', [None, '0' * 64])
def test_directory_is_invalid_with_or_without_checksum(tmp_path, checksum):
    ref = {'kind': 'custom', 'uri': '.'}
    if checksum:
        ref['sha256'] = checksum
    with pytest.raises(ReferenceError, match='not a regular file'):
        resolve_reference(ref, tmp_path)
    issues = semantic_issues({'mapping': {'ref': ref}}, tmp_path)
    assert any(x.code == 'artifact-reference-invalid' and x.path == '$.mapping.ref' for x in issues)


def test_unreadable_checksum_artifact_becomes_validation_finding(tmp_path, monkeypatch):
    (tmp_path / 'artifact').write_bytes(b'content')
    def denied(self):
        raise PermissionError('synthetic denial, no permissions changed')
    monkeypatch.setattr(Path, 'read_bytes', denied)
    ref = {'uri': 'artifact', 'sha256': '0' * 64}
    issues = semantic_issues({'mapping': {'ref': ref}}, tmp_path)
    assert any(x.code == 'artifact-reference-invalid' and 'cannot be read' in x.message for x in issues)


def test_missing_artifact_retains_existing_error(tmp_path):
    with pytest.raises(ReferenceError, match='does not exist'):
        resolve_reference({'uri': 'absent'}, tmp_path)


def test_regular_file_symlink_remains_supported(tmp_path):
    p = tmp_path / 'artifact'
    p.write_bytes(b'content')
    (tmp_path / 'alias').symlink_to(p)
    ref = {'uri': 'alias', 'sha256': hashlib.sha256(b'content').hexdigest()}
    assert resolve_reference(ref, tmp_path).verified


@pytest.mark.skipif(not hasattr(os, 'mkfifo'), reason='POSIX FIFO fixture')
def test_fifo_rejected_before_attempting_blocking_read(tmp_path, monkeypatch):
    os.mkfifo(tmp_path / 'pipe')
    def forbidden(self):
        pytest.fail('Nonregular artifact must not be read')
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    with pytest.raises(ReferenceError, match='not a regular file'):
        resolve_reference({'uri': 'pipe', 'sha256': '0' * 64}, tmp_path)


def test_remote_reference_stays_unfetched(tmp_path):
    ref = resolve_reference({'uri': 'https://example.invalid/artifact', 'sha256': '0' * 64}, tmp_path)
    assert ref.local_path is None and not ref.verified


@pytest.mark.parametrize('error', [PermissionError('synthetic traversal denial'), RuntimeError('synthetic symlink loop')])
def test_resolution_errors_become_validation_findings(tmp_path, monkeypatch, error):
    def denied(self, *args, **kwargs):
        raise error
    monkeypatch.setattr(Path, 'resolve', denied)
    issues = semantic_issues({'mapping': {'ref': {'uri': 'nested/artifact'}}}, tmp_path)
    assert any(x.code == 'artifact-reference-invalid' and 'cannot be resolved' in x.message for x in issues)
