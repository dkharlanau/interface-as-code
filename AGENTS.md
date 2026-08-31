# Agent instructions

Interface as Code is contract-first. Treat interface YAML and referenced specifications as authoritative inputs; do not fill gaps with assumptions from a vendor or protocol.

## Working loop

1. Read `README.md`, the relevant interface contract, and `docs/agent-manifest.json`.
2. Validate before readiness checks, comparison, drift analysis, or generation.
3. Inspect contract, implementation binding, runbook, and acceptance requirements as separate concerns.
4. When proposing a change, show what contract surface changes and which evidence or compatibility checks are affected.
5. Keep generated or emitted artifacts distinct from hand-authored source.

## Guardrails

- Do not invent endpoints, fields, ownership, recovery procedures, SLAs, or acceptance criteria.
- Do not treat a successful schema check as proof of operational readiness.
- Prefer read/inspect/diff/drift operations before any source modification.
- Preserve deterministic output and stable identifiers.
- Follow interoperability references to Mapping as Code or graph tools instead of duplicating their data.

## Useful commands

```bash
interface-as-code validate examples/
interface-as-code check examples/ --fail-on error
interface-as-code render examples/sap-mdg-to-s4-customer/interface.yaml
interface-as-code controls examples/sap-mdg-to-s4-customer/interface.yaml
interface-as-code catalog examples/ --output generated/catalog
```
