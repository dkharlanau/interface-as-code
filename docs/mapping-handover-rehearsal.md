# Mapping to support handover: a verified boundary, not a runtime integration

The producer can accept a binding while the consumer rejects it. A fresh synthetic
rehearsal found why: Mapping as Code writes a **canonical JSON hash**, while
Interface as Code verifies the **actual bytes** of local referenced artifacts.
The same mapping in ordinary YAML has different bytes. Do not remove the hash or
disable validation to make the handoff look successful.

## Reproduce

Use trusted clean Mapping as Code checkout at
`d06bd6ce1d00b02c5dfcc32815f958758f91d86c`, and this IaC candidate with Python and
its declared PyYAML/jsonschema dependencies. The tested consumer core is
`17171a9481121c4f604773f14c61acb62fa134d3`. The script is a standalone opt-in
compatibility rehearsal, not part of ordinary pytest or a new binding protocol.

```sh
python scripts/rehearse_mapping_handover.py --mapping-root /path/to/mapping-as-code
```

It calls both existing CLIs, uses temporary synthetic files, performs no network
requests and leaves the source checkouts unchanged. Review source before running.
It refuses a dirty Mapping checkout, records its actual commit, and fails if the
expected behavior changes. That failure should trigger review, not a relaxed test.
The Mapping PR #15 lifecycle implementation is not used or modified.

## Nine observed commands

1. Mapping validation succeeds, then its existing binding command succeeds.
2. IaC rejects the bound YAML reference: canonical hash `dad825c4…` differs from
   raw YAML hash `f920ae89…`.
3. The same synthetic mapping is serialized as canonical JSON: UTF-8, sorted keys,
   compact separators, no added newline. Mapping validation and binding succeed;
   IaC validation now succeeds because raw and canonical hashes coincide.
4. IaC generates a handover report but exits **1**, correctly preserving existing
   operational-readiness gaps. Acceptance remains `not_assessed`, replay remains
   `not_granted`. Successful binding is not production readiness.
5. Appending only a newline to that JSON makes IaC validation fail again. The
   existing consumer contract is byte integrity, not semantic equivalence.
6. Binding a deliberately different target system fails with exit **2**, without
   writing a bound output. The endpoint exception flag is not used.

The [machine-readable receipt](verification/mapping-handover-20261112.json)
records every actual command exit, full hashes and the actual consumer Python/schema source hashes. Generated `mapping.json` is derived from the pinned YAML; it is not a file committed in the producer repository. The rehearsal process itself
exits 0 only when all those positive **and expected-negative** outcomes hold.

## What this enables and what remains open

The controlled canonical-JSON artifact provides a tested way to pass this example
between the existing tools without weakening integrity. It is not a universal
canonicalization standard: these exact Python implementations, simple JSON-safe
mapping values and current loader behavior were exercised. Consumers must not
substitute a canonical hash for arbitrary raw files or silently rewrite originals.

Ordinary YAML binding remains incompatible at these versions. A future producer
fix needs an explicit decision about raw versus canonical identity and tests in
both tools, not another ad-hoc protocol. That fix belongs with the Mapping owner.
No mapping was executed, no target data reconciled and no SAP system contacted.
The report preserves existing operational fields rather than inventing owners,
recovery instructions or acceptance evidence. No human usefulness result is claimed.

### Optimized Python is not a bypass

The rehearsal uses explicit runtime guards, not Python `assert` statements, for
receipt evidence. `python -O` and `python -OO` must not turn an unexpected
acceptance grant, changed operational fields or the wrong rejection reason into
a successful receipt. Ten regression tests check the guards in all three
interpreter modes and prohibit optimizable assertions in this verifier.

A synthetic negative replay injected `acceptance.status: accepted` into the
handover response while running the complete rehearsal with `-O`. It exited 1
with no stdout receipt. The unmodified optimized rehearsal completed its nine
expected CLI cases. This verifies the diagnostic's fail-closed behavior, not
operational acceptance or SAP runtime behavior.
