"""Receipt evidence must not disappear when Python optimizations are enabled."""
import ast
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/rehearse_mapping_handover.py"


def test_rehearsal_has_no_optimizable_evidence_assertions():
    tree = ast.parse(SCRIPT.read_text())
    assert not any(isinstance(node, ast.Assert) for node in ast.walk(tree))


@pytest.mark.parametrize("optimization", [[], ["-O"], ["-OO"]])
def test_guard_rejects_false_evidence_without_success_receipt(optimization):
    code = f'''import runpy
module = runpy.run_path({str(SCRIPT)!r})
module["require"](False, "synthetic rejected evidence")
print("SUCCESS RECEIPT")
'''
    result = subprocess.run([sys.executable, *optimization, "-c", code],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert "ValueError: synthetic rejected evidence" in result.stderr
    assert not result.stdout


@pytest.mark.parametrize("optimization", [[], ["-O"], ["-OO"]])
def test_guard_preserves_valid_evidence(optimization):
    code = f'''import runpy
module = runpy.run_path({str(SCRIPT)!r})
module["require"](True, "unused")
print("checked")
'''
    result = subprocess.run([sys.executable, *optimization, "-c", code],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "checked\n"


@pytest.mark.parametrize("optimization", [[], ["-O"], ["-OO"]])
def test_full_rehearsal_rejects_injected_acceptance(optimization, tmp_path):
    # Synthetic subprocess boundary: exercise orchestration without a second
    # repository, network, SAP system, or an actual acceptance decision.
    code = f'''import hashlib, json, runpy, subprocess, tempfile
from pathlib import Path
import yaml
module = runpy.run_path({str(SCRIPT)!r})
root = Path({str(tmp_path)!r})
(root / "examples").mkdir()
(root / "examples/customer-master.yaml").write_text("mapping: synthetic\\n")
(root / "examples/customer-interface.yaml").write_text("interface: synthetic\\n")
subprocess.check_output = lambda args, **kw: "" if "status" in args else "synthetic-revision\\n"
count = 0
def fake_run(argv, **kw):
    global count
    count += 1
    command = argv[3]
    if command == "bind-interface":
        artifact = Path(argv[5])
        digest = hashlib.sha256(json.dumps(yaml.safe_load(artifact.read_text()), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        bound = {{"interface": "synthetic", "mapping": {{"ref": {{"sha256": digest}}}}}}
        Path(argv[argv.index("--output") + 1]).write_text(yaml.safe_dump(bound))
    if command == "handover":
        return subprocess.CompletedProcess(argv, 1, json.dumps({{"acceptance": {{"status": "accepted", "replay_authority": "not_granted"}}}}), "")
    return subprocess.CompletedProcess(argv, 1 if count == 3 else 0, "Checksum mismatch" if count == 3 else "", "")
subprocess.run = fake_run
print(json.dumps(module["rehearse"](root)))
'''
    result = subprocess.run([sys.executable, *optimization, "-c", code],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert "Handover unexpectedly claimed acceptance." in result.stderr
    assert not result.stdout
