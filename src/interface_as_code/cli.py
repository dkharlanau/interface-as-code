from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .loader import SpecLoadError, load_yaml
from .renderer import render_markdown, render_mermaid
from .validator import validate_spec


def _validate(path: str) -> int:
    try:
        issues = validate_spec(path)
    except SpecLoadError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if issues:
        print(f"INVALID {path}")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print(f"VALID {path}")
    return 0


def _render(path: str, output: str | None, format_name: str) -> int:
    issues = validate_spec(path)
    if issues:
        print(f"INVALID {path}", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1

    spec = load_yaml(path)
    rendered = render_mermaid(spec) if format_name == "mermaid" else render_markdown(spec)

    if output:
        target = Path(output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
        print(f"WROTE {target}")
    else:
        print(rendered)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="iac",
        description="Validate and render Interface as Code specifications.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validate one interface specification.")
    validate.add_argument("spec")

    render = sub.add_parser("render", help="Render interface documentation.")
    render.add_argument("spec")
    render.add_argument("--format", choices=["markdown", "mermaid"], default="markdown")
    render.add_argument("-o", "--output")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "validate":
        raise SystemExit(_validate(args.spec))
    if args.command == "render":
        raise SystemExit(_render(args.spec, args.output, args.format))


if __name__ == "__main__":
    main()
