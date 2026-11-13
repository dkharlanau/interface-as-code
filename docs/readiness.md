# Production-readiness checks

`interface-as-code check` evaluates deterministic operational policies after structural validation.

```bash
interface-as-code check examples/reference-landscape
interface-as-code check . --format json
interface-as-code check . --fail-on error
```

Policies cover ownership, retry/replay, idempotency, dead-letter handling, monitoring signals, business correlation, reconciliation, SLA, test intent, security and batch scheduling. Each finding includes severity, a stable code, the affected path, why it matters and remediation guidance.

The tool intentionally avoids a black-box AI readiness score. Teams can gate on explicit findings and review policy changes in Git.

## A blank owner is still missing

Scalar operational fields containing only whitespace count as missing. This
includes spaces, tabs, line breaks and Unicode whitespace recognized by Python's
string trimming. Existing placeholders such as `TODO`, `TBD` and `UNASSIGNED`
remain missing; a real value with surrounding spaces is not rewritten.

The synthetic REST handover variant illustrates the distinction:

```sh
interface-as-code validate examples/governance/blank-operational-values.yaml
# Exit 0: the contract satisfies structural validation.
interface-as-code check examples/governance/blank-operational-values.yaml \
  --format json --fail-on error
# Exit 1: owner.missing and support.route-missing require answers.
```

A minimum string length cannot establish ownership or an operational destination.
The report preserves the existing finding code, severity, affected contract path
and remediation. No owner, queue or recovery procedure is inferred. Correct the
source with a real accountable team and support route, then check again.

This strengthens the existing scalar missing-value policies; it does not validate
the meaning of every sentence or the content of list-valued monitoring signals.
Structural validation, readiness and demonstrated runtime behavior remain separate.
`--fail-on none` still emits findings with exit 0 by explicit request; it is not an
approval. Existing custom policy packs retain their declared overrides. Generated
controls and test plans are still plans, not executed checks or replay authority.

## An empty selection is not a passing readiness check

A missing directory or a directory containing no discoverable interface.yaml
files is an input error: check returns exit 2, writes a diagnostic to stderr,
and emits no Markdown, JSON or GitHub report. This applies even with
--fail-on none. The threshold controls findings in checked contracts, not whether
any contract was supplied.

For the reference landscape, import inventory.csv into a generated directory
first, then pass that generated directory to check. The inventory source folder
itself contains no materialized interface.yaml files.

This tightens the previous standalone behavior, which returned 0 (and [] in JSON)
for an empty selection. Scripts intentionally tolerating empty inventories must
handle absence explicitly rather than treating it as readiness evidence. The
bundled GitHub Action already runs validate first and rejects this case.
Nonempty selections retain their existing output shape and severity thresholds.

Empty-selection errors are reported before policy packs or overlays are loaded.
