"""A policy typo must not silently lower the readiness gate."""
import os
import subprocess
import sys
from pathlib import Path
import pytest
import yaml
from interface_as_code.governance import apply_policy_pack, load_policy_pack
from interface_as_code.policies import Finding

ROOT = Path(__file__).resolve().parents[1]
BAD = ["erorr", "ERROR", "", None, False, 2, ["error"], {"value": "error"}]

@pytest.mark.parametrize("severity", BAD)
def test_invalid_severity_rejected_even_without_matching_findings(tmp_path, severity):
    pack = {"rules": {"unknown.rule": {"severity": severity}}}
    with pytest.raises(ValueError, match="severity"):
        apply_policy_pack([], pack)
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(pack))
    with pytest.raises(ValueError, match="severity"):
        load_policy_pack(path)

@pytest.mark.parametrize("format_name", ["markdown", "json", "github"])
@pytest.mark.parametrize("threshold", ["error", "none"])
def test_cli_typo_is_input_error_without_report(tmp_path, format_name, threshold):
    policy = tmp_path / "typo.yaml"
    policy.write_text("rules:\n  owner.missing: {severity: erorr}\n  support.route-missing: {severity: erorr}\n")
    result = subprocess.run(
        [sys.executable, "-m", "interface_as_code.cli", "check",
         str(ROOT / "examples/governance/blank-operational-values.yaml"),
         "--policy", str(policy), "--format", format_name, "--fail-on", threshold],
        env=dict(os.environ, PYTHONPATH=str(ROOT / "src")), capture_output=True, text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "severity" in result.stderr
    assert "Traceback" not in result.stderr

@pytest.mark.parametrize("severity", ["error", "warning", "info"])
def test_supported_override_and_explicit_disable_remain_supported(severity):
    finding = Finding("error", "example.rule", "$.x", "Message", "Remediation")
    assert apply_policy_pack([finding], {"rules": {"example.rule": {"severity": severity}}})[0].severity == severity
    assert apply_policy_pack([finding], {"rules": {"example.rule": False}}) == []
    assert apply_policy_pack([finding], {"rules": {"example.rule": {"enabled": False}}}) == []


def test_omitted_severity_keeps_original_finding():
    finding = Finding("error", "example.rule", "$.x", "Message", "Remediation")
    assert apply_policy_pack([finding], {"rules": {"example.rule": {}}}) == [finding]

def test_disabled_rule_does_not_hide_invalid_severity():
    with pytest.raises(ValueError, match="severity"):
        apply_policy_pack([], {"rules": {"unknown.rule": {"enabled": False, "severity": "erorr"}}})
