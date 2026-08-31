from __future__ import annotations

import json
import re
from pathlib import Path

from interface_as_code.cli import build_parser


ROOT = Path(__file__).parents[1]
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
AUTHOR_FOOTER = """## About the author

Created and maintained by **Dzmitryi Kharlanau**, an SAP consultant and system analyst working across enterprise architecture, data, integration, operations, and practical AI.

- [Website and knowledge base](https://dkharlanau.github.io/)
- [LinkedIn](https://www.linkedin.com/in/dkharlanau/)"""


def test_local_markdown_links_resolve():
    documents = [
        ROOT / "README.md",
        ROOT / "PRODUCT.md",
        ROOT / "BACKLOG.md",
        ROOT / "CONTRIBUTING.md",
        *sorted((ROOT / "docs").glob("*.md")),
        *sorted((ROOT / "examples").rglob("README.md")),
    ]
    broken: list[str] = []
    for document in documents:
        for raw_target in LINK_RE.findall(document.read_text(encoding="utf-8")):
            target = raw_target.strip().split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (document.parent / target).resolve().exists():
                broken.append(f"{document.relative_to(ROOT)} -> {raw_target}")
    assert not broken, "Broken local documentation links:\n" + "\n".join(broken)


def test_agent_manifest_uses_supported_public_cli_commands():
    manifest = json.loads((ROOT / "docs" / "agent-manifest.json").read_text(encoding="utf-8"))
    parser = build_parser()
    command_action = next(action for action in parser._actions if action.dest == "command")
    supported = set(command_action.choices)
    advertised = {entry["command"].split()[1] for entry in manifest["entrypoints"] if entry["type"] == "cli"}
    assert advertised <= supported


def test_public_agent_guidance_does_not_advertise_retired_interface():
    guidance = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in ("AGENTS.md", "docs/agent-manifest.json", "docs/product.html")
    )
    assert "python -m iac" not in guidance
    for command in ("interface-as-code inspect", "interface-as-code runbook", "interface-as-code attest"):
        assert command not in guidance


def test_readme_ends_with_exact_author_footer_and_suite_guide():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").rstrip()
    assert readme.endswith(AUTHOR_FOOTER)
    assert readme.count("## About the author") == 1
    assert "docs/as-code-suite.md" in readme
    for repository in ("decision-tables-as-code", "mapping-as-code", "process-as-code", "reconciliation-as-code"):
        assert f"https://github.com/dkharlanau/{repository}" in readme


def test_agent_manifest_navigates_the_core_suite():
    manifest = json.loads((ROOT / "docs" / "agent-manifest.json").read_text(encoding="utf-8"))
    assert {item["product"] for item in manifest["related"]} == {
        "decision-tables-as-code", "mapping-as-code", "process-as-code", "reconciliation-as-code"
    }
