# Specification drift

A matching value is only useful when the observation is usable. A missing path is
not an explicit null, and an unreadable timestamp is not evidence that a value is
current. `interface-as-code drift` compares a validated interface contract with
source-attributed offline observations. It never edits the contract, executes an
integration, grants replay approval or proves production readiness.

## Review one observation set

```bash
interface-as-code drift examples/rest-order-api/interface.yaml \
  examples/governance/drift-hardening-evidence.yaml \
  --evaluated-at 2026-11-08T12:00:00Z --stale-after-days 1 \
  --format report-json --require-complete --fail-on-drift
```

This synthetic handover example intentionally exits **2**. It contains one
comparable match, one invalid timestamp, one missing declared path, one absent
observed value and one unavailable observation. The last four do not establish a
current match. Correct the evidence before using it to accept a handover. The
fixture is a demonstration, not an observation of a real enterprise system.

The CLI validates the interface and local artifact references before comparison.
The Python `compare_evidence` function expects an already validated contract.
Paths use `$.key.path` dictionary traversal; array indexing and empty segments
are unsupported and reported as invalid. `value: null` is a present value and can
match a present null declaration. An omitted `value` or missing declared path
cannot match, even if both are absent.

## Time is part of the evidence

With `--stale-after-days N`:

- N must be a nonnegative whole number. A day is exactly 86,400 elapsed seconds.
- Both the observation and explicit evaluation time must use
  `YYYY-MM-DDTHH:MM:SS[.ffffff]` with `Z` or a valid `±HH:MM` UTC offset.
  Seconds are required; fractional precision is at most six digits. Naive local times and date-only values are not interpreted using
  the host's timezone.
- Age exactly equal to the limit is comparable. Any older observation is stale.
- Observations later than the evaluation instant are unknown. There is no
  implicit clock-skew allowance.
- Missing, malformed or ambiguous observation times are unknown, not drift or
  match. An invalid explicit evaluation time rejects the command with exit 2.

Without a freshness limit, timestamp validity and age are **not checked**. This
preserves descriptive comparisons for existing callers. A match in that mode
means only equal values, not current or recent evidence.

`--evaluated-at` fixes the instant for reproducible output. Omit it to capture the
current UTC time once per comparison. Record the returned instant and reuse it
when replaying a review; do not replace an old instant with today's date. The
same inputs, policy and explicit instant produce the same JSON independent of
the machine's timezone.

## Read the outcome, not just the process exit

Findings retain their source, path and observed timestamp:

- `match` / `drift`: comparable values agree / differ.
- `unknown`: a path, value or usable freshness timestamp is missing.
- `invalid`: an observation, path or status is malformed. Bad rows are retained
  as findings instead of being silently skipped.
- `stale` / `unavailable`: retained noncomparability, including these explicit
  input statuses. They may omit a value; they never become a match.
- `conflict`: two otherwise comparable observations in the same set disagree
  on one path. No source is silently chosen as authoritative. Separate historical
  snapshots or resolve the conflicting sources before retrying. Duplicate equal
  observations remain comparable. Stale/unavailable rows do not compete with a
  fresh value but still make the set incomplete.

Compared values must be finite JSON-compatible data: null, booleans, numbers,
strings, lists or objects with string keys, without cycles and within depth 100.
YAML sets, binary values and non-finite numbers are invalid, not coerced to
strings. The evidence loader preserves timestamp/date scalars as their original
text, so YAML cannot normalize a malformed timestamp before validation. Python
API business values that are date objects are unsupported. Unsupported values are retained as null with an
`invalid_value` reason, not as a claim that the original observation was null.
Quote dates used as business values to make the intended string type clear. Source identifiers must be nonempty strings.

Accepted input statuses are `observed` (the default), `stale` and `unavailable`.
An input that claims `match`, `accepted` or any other status is not trusted.

`--format report-json` emits `interface-as-code-drift-report/1.0`, including
`evaluated_at`, `freshness_policy`, `freshness_checked`, `counts`, `complete`,
`outcome` and `findings`. An empty observation list is incomplete and inconclusive.
Any unresolved finding makes the overall outcome inconclusive, even if another
row proves drift; inspect the counts and individual findings as well.

- Default display mode returns 0 after a valid comparison, even if inconclusive.
- `--fail-on-drift` returns 1 when any finding is `drift` or `conflict`.
  Conflicting observations must not turn an existing drift gate green.
- `--require-complete` returns 2 for unresolved or empty evidence, taking
  precedence over the drift exit. Use **both flags** for a complete no-drift gate.
- Invalid documents, options or interface contracts return 2 with an error.

Exit 0 is not operational acceptance. Even a complete, fresh no-drift result only
covers the supplied observations, not every contract field or the integration's
actual behavior. Sources and timestamps are claims supplied by the collector;
this command does not authenticate them.

## Compatibility and retained-output migration

The interface specification remains v1.0; no contract fields or schemas change.
`compare_evidence` still returns a list of `DriftFinding`, and `--format json`
still emits a top-level list. Findings have additive `declared_present`,
`observed_present`, `reason_code`, `evaluated_at` and `stale_after_days` metadata.
The Python API accepts the optional keyword `evaluated_at` as an aware datetime
or ISO 8601 string. Existing calls without it capture one current UTC instant.

Consumers must handle the new `unknown`, `invalid` and `conflict` statuses as
noncomparability; do not treat every non-drift status as a match. Missing
observation lists, malformed documents and invalid contracts are now rejected.
Malformed individual rows are reported, not discarded. Empty lists remain legal,
but provide no verification. This deliberately tightens previously misleading
behavior. Update strict output validators and acceptance scripts before adopting
the prepared patch. Use the opt-in versioned report format when retaining reviews,
especially empty sets, which cannot carry metadata in the legacy list alone.

This is a local preparation for issue #28. No package version, release, published
schema, license or deployment has been changed by the preparation.
