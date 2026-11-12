"""Keep metadata bound to the existing repository license notice."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def test_metadata_identifies_bundled_notice_instead_of_stale_mit():
    metadata = (ROOT / "pyproject.toml").read_text()
    assert re.search(r'(?m)^license = "LicenseRef-Interface-As-Code"$', metadata)
    assert re.search(r'(?m)^license-files = \["LICENSE"\]$', metadata)

def test_license_notice_retains_distinct_scopes_and_prior_rights():
    notice = (ROOT / "LICENSE").read_text()
    assert "PolyForm Strict License 1.0.0" in notice
    assert "All Rights Reserved" in notice
    assert "does not revoke rights already granted" in notice
