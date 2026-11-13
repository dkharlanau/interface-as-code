"""Build retained, declaration-only agent context without adding runtime authority."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from .handover import _build_handover


def handover_projection(path: Path, raw: bytes, spec: dict[str, Any]) -> dict[str, Any]:
    """Reuse the handover policy/questions while omitting bulky controls and plans."""
    report = _build_handover(path, raw, spec)
    return {"format": "interface-as-code-catalog-handover/1.0",
            **{key: report[key] for key in (
                "source", "acceptance", "declared_contacts", "readiness", "review_prompts", "limits")}}


def snapshot_provenance(path: Path, raw: bytes, context: dict) -> dict[str, Any]:
    """A repository HEAD alone must not attest edited or untracked source bytes."""
    revision = context.get("revision")
    root = context.get("repo_root")
    result = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
              "revision": None, "repository_revision": revision,
              "source_state": "no_repository",
              "binding_scope": "Validated source YAML bytes only; referenced artifacts are not bundled or attested."}
    if not root or not revision:
        return result
    try:
        relative = path.resolve().relative_to(Path(root).resolve()).as_posix()
    except (OSError, RuntimeError, ValueError):
        result["source_state"] = "outside_repository"
        return result
    try:
        committed = subprocess.run(["git", "cat-file", "blob", f"{revision}:{relative}"],
                                   cwd=root, capture_output=True, check=False)
    except OSError:
        result["source_state"] = "revision_unverified"
        return result
    if committed.returncode == 0 and committed.stdout == raw:
        result.update(revision=revision, source_state="committed")
    else:
        result["source_state"] = "modified_or_untracked"
    return result
