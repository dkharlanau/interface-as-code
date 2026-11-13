"""A standalone readiness gate must not pass when it checked no contracts."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize("selection", ["empty-directory", "missing-directory"])
@pytest.mark.parametrize("format_name", ["markdown", "json", "github"])
@pytest.mark.parametrize("threshold", ["error", "warning", "info", "none"])
def test_empty_readiness_selection_is_input_error(tmp_path, selection, format_name, threshold):
    path = tmp_path / selection
    if selection == "empty-directory":
        path.mkdir()
        (path / "README.md").write_text("Synthetic inventory export contains no interface.yaml files.\n")
    result = subprocess.run(
        [sys.executable, "-m", "interface_as_code.cli", "check", str(path),
         "--format", format_name, "--fail-on", threshold],
        cwd=ROOT, env=dict(os.environ, PYTHONPATH=str(ROOT / "src")),
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "no interface.yaml files found" in result.stderr

def test_populated_landscape_retains_json_output_and_disabled_gate(tmp_path):
    from interface_as_code.importer import import_csv
    generated = tmp_path / "landscape"
    import_csv(ROOT / "examples/reference-landscape/inventory.csv", generated)
    result = subprocess.run(
        [sys.executable, "-m", "interface_as_code.cli", "check",
         str(generated), "--format", "json", "--fail-on", "none"],
        cwd=ROOT, env=dict(os.environ, PYTHONPATH=str(ROOT / "src")),
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    rows = json.loads(result.stdout)
    assert len(rows) == 30
    assert all("spec" in row and "findings" in row for row in rows)
