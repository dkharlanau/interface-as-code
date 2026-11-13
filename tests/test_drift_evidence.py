from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from interface_as_code.drift import build_drift_report, compare_evidence, load_evidence

ROOT = Path(__file__).parents[1]
SPEC = {"interface": {"id": "ORDER-API-01"}, "nullable": None}
AT = "2026-11-08T12:00:00Z"


def observation(**changes):
    return {"path": "$.interface.id", "value": "ORDER-API-01", "source": "synthetic-inventory", "observed_at": AT, **changes}


def findings(*rows, **options):
    return compare_evidence(SPEC, {"observations": list(rows)}, evaluated_at=AT, **options)


@pytest.mark.parametrize("time", [None, "not-a-date", "2026-11-08", "2026-11-08T12:00:00", 123, [], {}, ""])
def test_invalid_time_is_unknown_with_freshness(time):
    got = findings(observation(observed_at=time), stale_after_days=1)[0]
    assert got.status == "unknown" and got.reason_code == "invalid_observed_at"


def test_old_public_call_fails_closed_without_new_options():
    got = compare_evidence(SPEC, {"observations": [observation(observed_at="not-a-date")]}, stale_after_days=1)
    assert got[0].status == "unknown"


def test_missing_time_is_unknown_with_freshness():
    obs = observation(); del obs["observed_at"]
    assert findings(obs, stale_after_days=1)[0].status == "unknown"


@pytest.mark.parametrize(("time", "expected"), [
    ("2026-11-07T12:00:00Z", "match"),
    ("2026-11-07T11:59:59.999999Z", "stale"),
    ("2026-11-08T12:00:00.000001Z", "unknown"),
    ("2026-11-08T15:00:00+03:00", "match"),
    ("2026-11-08T07:00:00-05:00", "match"),
])
def test_exact_freshness_boundary_future_and_timezone(time, expected):
    assert findings(observation(observed_at=time), stale_after_days=1)[0].status == expected


def test_zero_day_limit_is_instant_not_calendar_day():
    assert findings(observation(), stale_after_days=0)[0].status == "match"
    assert findings(observation(observed_at="2026-11-08T11:59:59Z"), stale_after_days=0)[0].status == "stale"


@pytest.mark.parametrize("limit", [-1, True, 1.5, "1"])
def test_invalid_freshness_config_rejected(limit):
    with pytest.raises(ValueError, match="nonnegative"):
        findings(observation(), stale_after_days=limit)


@pytest.mark.parametrize("time", ["not-a-date", "2026-11-08T12:00:00", "2026-11-08", 123])
def test_invalid_evaluation_instant_rejected(time):
    with pytest.raises(ValueError):
        compare_evidence(SPEC, {"observations": []}, evaluated_at=time)


def test_absences_are_not_null_match():
    got = findings({"path": "$.absent"})[0]
    assert got.status == "unknown" and not got.declared_present and not got.observed_present
    got = findings({"path": "$.interface.id"})[0]
    assert got.status == "unknown" and got.reason_code == "observed_value_absent"
    got = findings({"path": "$.nullable", "value": None})[0]
    assert got.status == "match" and got.declared_present and got.observed_present
    assert findings({"path": "$.absent", "value": None})[0].status == "unknown"


@pytest.mark.parametrize("row", [None, [], "text", 7, {}, {"path": 7}, {"path": "$"}, {"path": "$."}, {"path": "$.interface..id"}, {"path": "$.items[0]"}])
def test_malformed_observations_are_retained(row):
    got = findings(row)
    assert len(got) == 1 and got[0].status == "invalid" and got[0].message


@pytest.mark.parametrize("status", ["accepted", "match", "unknown", None, [], {}])
def test_unsupported_status_is_not_trusted(status):
    got = findings(observation(status=status))[0]
    assert got.status == "invalid" and got.reason_code == "unsupported_status"


@pytest.mark.parametrize("status", ["unavailable", "stale"])
def test_explicit_noncomparability_is_preserved(status):
    got = findings({"path": "$.interface.id", "status": status}, stale_after_days=1)[0]
    assert got.status == status and not got.observed_present


def test_conflicting_comparable_observations_are_not_ordered_by_authority():
    rows = [observation(), observation(value="OTHER", source="other-inventory")]
    assert [x.status for x in findings(*rows)] == ["conflict", "conflict"]
    assert [x.status for x in findings(*reversed(rows))] == ["conflict", "conflict"]
    assert [x.status for x in findings(observation(), observation())] == ["match", "match"]
    # A stale snapshot is unresolved, not a competing fresh value.
    assert [x.status for x in findings(observation(), observation(value="OTHER", observed_at="2026-01-01T00:00:00Z"), stale_after_days=1)] == ["match", "stale"]


def test_bool_is_not_integer_in_nested_values():
    got = compare_evidence({"x": {"value": [True]}}, {"observations": [{"path": "$.x", "value": {"value": [1]}}]}, evaluated_at=AT)
    assert got[0].status == "drift"


def test_no_freshness_comparison_does_not_claim_freshness():
    report = build_drift_report(SPEC, {"observations": [observation(observed_at="not-a-date")]}, evaluated_at=AT)
    assert report["outcome"] == "match" and report["freshness_checked"] is False
    assert report["freshness_policy"]["stale_after_days"] is None


def test_empty_evidence_has_policy_but_is_not_verification():
    report = build_drift_report(SPEC, {"observations": []}, evaluated_at=AT, stale_after_days=1)
    assert report["outcome"] == "inconclusive" and report["complete"] is False
    assert report["evaluated_at"] == AT and report["freshness_checked"] is True


@pytest.mark.parametrize("evidence", [None, [], {}, {"observations": None}, {"observations": {}}, {"observations": ""}])
def test_bad_document_structure_rejected(evidence):
    with pytest.raises(ValueError):
        compare_evidence(SPEC, evidence, evaluated_at=AT)


def cli(path, *args, timezone="UTC", spec=None):
    return subprocess.run(
        [sys.executable, "-B", "-m", "interface_as_code.cli", "drift", str(spec or ROOT / "examples/rest-order-api/interface.yaml"), str(path), *args],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "TZ": timezone},
    )


def write_evidence(tmp_path, rows):
    p = tmp_path / "evidence.yaml"; p.write_text(yaml.safe_dump({"observations": rows})); return p


def test_public_cli_old_shape_rejects_false_current_match(tmp_path):
    p = write_evidence(tmp_path, [observation(observed_at="not-a-date")])
    run = cli(p, "--format", "json", "--stale-after-days", "1")
    assert run.returncode == 0  # Compatibility: display mode is not an acceptance gate.
    assert isinstance(json.loads(run.stdout), list)
    assert json.loads(run.stdout)[0]["status"] == "unknown"


def test_public_cli_fixed_time_has_identical_bytes_across_host_timezones(tmp_path):
    p = write_evidence(tmp_path, [observation(observed_at="2026-11-08T15:00:00+03:00")])
    options = ("--format", "report-json", "--evaluated-at", AT, "--stale-after-days", "1", "--require-complete", "--fail-on-drift")
    runs = [cli(p, *options, timezone=tz) for tz in ("UTC", "America/Los_Angeles", "Pacific/Kiritimati")]
    assert all(r.returncode == 0 for r in runs)
    assert len({r.stdout for r in runs}) == 1
    assert json.loads(runs[0].stdout)["outcome"] == "match"


@pytest.mark.parametrize(("rows", "expected"), [([observation()], 0), ([observation(value="OTHER")], 1), ([observation(observed_at="bad")], 2), ([], 2), ([observation(), observation(value="OTHER")], 2)])
def test_cli_complete_gate_and_drift_have_distinct_exits(tmp_path, rows, expected):
    p = write_evidence(tmp_path, rows)
    run = cli(p, "--format", "report-json", "--evaluated-at", AT, "--stale-after-days", "1", "--require-complete", "--fail-on-drift")
    assert run.returncode == expected and "Traceback" not in run.stderr


def test_invalid_spec_rejected_before_observations(tmp_path):
    p = write_evidence(tmp_path, [observation()]); spec = tmp_path / "interface.yaml"; spec.write_text("interface: {}\n")
    run = cli(p, "--format", "json", spec=spec)
    assert run.returncode == 2 and "invalid interface contract" in run.stderr and not run.stdout


@pytest.mark.parametrize("text", ["[]", "", "observations: nope", "observations: ["])
def test_bad_evidence_cli_has_clean_error(tmp_path, text):
    p = tmp_path / "bad.yaml"; p.write_text(text)
    run = cli(p, "--format", "json")
    assert run.returncode == 2 and "ERROR" in run.stderr and "Traceback" not in run.stderr


def test_cli_markdown_names_inconclusive_and_policy(tmp_path):
    p = write_evidence(tmp_path, [{"path": "$.missing"}])
    run = cli(p, "--evaluated-at", AT, "--stale-after-days", "1")
    assert "INCONCLUSIVE" in run.stdout and AT in run.stdout and "UNKNOWN" in run.stdout


def test_unquoted_yaml_timestamp_supported(tmp_path):
    p = tmp_path / "time.yaml"; p.write_text("observations:\n  - path: $.interface.id\n    value: ORDER-API-01\n    observed_at: 2026-11-08T12:00:00Z\n")
    assert compare_evidence(SPEC, load_evidence(str(p)), evaluated_at=AT, stale_after_days=0)[0].status == "match"


def test_documented_handover_fixture_is_inconclusive():
    p = ROOT / "examples/governance/drift-hardening-evidence.yaml"
    run = cli(p, "--evaluated-at", AT, "--stale-after-days", "1", "--format", "report-json", "--require-complete", "--fail-on-drift")
    report = json.loads(run.stdout)
    assert run.returncode == 2
    assert report["counts"] == {"match": 1, "unavailable": 1, "unknown": 3}
    assert report["outcome"] == "inconclusive"


@pytest.mark.parametrize("time", ["2026-11-08T12:00:00+00:60", "2026-11-08X12:00:00Z", "2026-11-08T12:00:00+24:00", "2026-11-08T12:00:00.1234567Z", "2026-11-08T12:00Z"])
def test_malformed_iso_is_not_normalized_to_fresh(time):
    got = findings(observation(observed_at=time), stale_after_days=1)[0]
    assert got.status == "unknown"


def test_legacy_fail_on_drift_stays_nonzero_for_conflicts(tmp_path):
    p = write_evidence(tmp_path, [observation(), observation(value="OTHER")])
    assert cli(p, "--fail-on-drift", "--format", "report-json", "--evaluated-at", AT).returncode == 1


@pytest.mark.parametrize("value", [{"alpha", "beta"}, b"binary", float("nan"), float("inf"), {1: "numeric key"}])
def test_unsupported_values_are_invalid_not_stringified(value):
    got = findings(observation(value=value))[0]
    assert got.status == "invalid" and got.reason_code == "invalid_value" and got.observed is None
    json.dumps(got.to_dict(), allow_nan=False)


def test_cyclic_values_are_invalid():
    value = []; value.append(value)
    assert findings(observation(value=value))[0].status == "invalid"


def test_unknown_yaml_values_are_stable_across_hash_seeds(tmp_path):
    p = tmp_path / "set.yaml"
    p.write_text("observations:\n  - path: $.interface.id\n    value: !!set {alpha: null, beta: null, gamma: null}\n")
    command = [sys.executable, "-m", "interface_as_code.cli", "drift", str(ROOT / "examples/rest-order-api/interface.yaml"), str(p), "--format", "report-json", "--evaluated-at", AT, "--require-complete"]
    runs = [subprocess.run(command, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONHASHSEED": seed}) for seed in ("1", "2")]
    assert all(r.returncode == 2 for r in runs) and runs[0].stdout == runs[1].stdout


@pytest.mark.parametrize("source", [None, "", [], {"x", "y"}, {"a": "b"}])
def test_malformed_source_is_actionable(source):
    got = findings(observation(source=source))[0]
    assert got.status == "invalid" and got.reason_code == "invalid_source"


@pytest.mark.parametrize("time", ["2026-11-08T12:00:00+00:60", "2026-11-08T12:00:00.1234567Z", "2026-11-08 12:00:00Z"])
def test_yaml_cannot_normalize_bad_timestamp_before_validation(tmp_path, time):
    p = tmp_path / "raw-time.yaml"
    p.write_text(f"observations:\n  - path: $.interface.id\n    value: ORDER-API-01\n    observed_at: {time}\n")
    assert load_evidence(str(p))["observations"][0]["observed_at"] == time
    run = cli(p, "--format", "report-json", "--evaluated-at", AT, "--stale-after-days", "1", "--require-complete")
    assert run.returncode == 2
    assert json.loads(run.stdout)["findings"][0]["status"] == "unknown"


def test_local_timestamp_loader_does_not_mutate_safe_load(tmp_path):
    p = tmp_path / "time.yaml"; p.write_text("observed_at: 2026-11-08T12:00:00Z")
    assert isinstance(load_evidence(str(p))["observed_at"], str)
    assert not isinstance(yaml.safe_load(p.read_text())["observed_at"], str)
