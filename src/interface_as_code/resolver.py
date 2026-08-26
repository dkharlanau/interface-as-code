from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

@dataclass(frozen=True)
class ResolvedReference:
    kind: str
    uri: str
    local_path: Path | None
    revision: str | None = None
    sha256: str | None = None
    verified: bool = False

class ReferenceError(ValueError):
    pass

def _is_external(uri: str) -> bool:
    scheme = urlparse(uri).scheme.lower()
    return scheme in {"http", "https", "git", "ssh"} or uri.startswith("git+")

def resolve_reference(ref: dict[str, Any], base_dir: Path, verify_checksum: bool = True) -> ResolvedReference:
    kind = str(ref.get("kind", "custom"))
    uri = str(ref.get("uri", ""))
    revision = ref.get("revision")
    expected = ref.get("sha256")
    if not uri:
        raise ReferenceError("Reference URI is empty.")
    if _is_external(uri):
        return ResolvedReference(kind, uri, None, revision, expected, False)
    parsed = urlparse(uri)
    if parsed.scheme == "file":
        path = Path(parsed.path)
    elif parsed.scheme:
        raise ReferenceError(f"Unsupported reference scheme: {parsed.scheme}")
    else:
        path = (base_dir / uri).resolve()
    if not path.exists():
        raise ReferenceError(f"Referenced artifact does not exist: {uri}")
    verified = False
    if expected and verify_checksum:
        actual = sha256(path.read_bytes()).hexdigest()
        if actual.lower() != expected.lower():
            raise ReferenceError(f"Checksum mismatch for {uri}: expected {expected}, got {actual}")
        verified = True
    return ResolvedReference(kind, uri, path, revision, expected, verified)

def iter_references(spec: dict[str, Any]):
    for section_name in ("contract", "mapping", "reconciliation"):
        section = spec.get(section_name, {})
        if isinstance(section, dict) and isinstance(section.get("ref"), dict):
            yield f"$.{section_name}.ref", section["ref"]
    for index, test in enumerate(spec.get("tests", [])):
        if isinstance(test, dict) and isinstance(test.get("evidence_ref"), dict):
            yield f"$.tests.{index}.evidence_ref", test["evidence_ref"]
    for index, item in enumerate(spec.get("evidence", [])):
        if isinstance(item, dict) and isinstance(item.get("ref"), dict):
            yield f"$.evidence.{index}.ref", item["ref"]
