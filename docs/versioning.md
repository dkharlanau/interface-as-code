# Specification and tool versioning

The Interface as Code specification and the CLI/package are versioned independently.

- `interface.yaml version: "1.0"` selects the v1.0 specification contract.
- Python package/CLI releases use semantic versioning independently.
- Versioned schemas live under `spec/v<spec-version>/interface.schema.json` and the currently supported schema is also packaged for offline CLI validation.
- Backward-compatible optional fields may be added within a specification line only when existing valid documents remain valid and their meaning does not change.
- A breaking semantic or structural change requires a new specification version, migration guidance and conformance fixtures.
- Published old schema/conformance directories are immutable compatibility targets; they are not rewritten to follow the latest package.

## Compatibility matrix

| CLI/package | Supported spec | Default authored spec | Migration behavior |
| --- | --- | --- | --- |
| 0.3.x | 1.0 | 1.0 | `1.0 → 1.0` deterministic no-op; unsupported source/target versions fail closed |

The table describes tested compatibility, not an assertion that future package versions will support every historical spec forever. When support changes, the release notes and this matrix must change together.

## Conformance contract

The public conformance suite lives under `conformance/v<spec-version>/`. It can be executed without importing Interface as Code internals:

```bash
python conformance/run.py --spec-version 1.0
```

The runner uses the published schema itself and verifies that every `valid/` fixture is accepted and every `invalid/` fixture is rejected. See [`conformance/README.md`](../conformance/README.md).

Third-party implementations therefore have three stable inputs:

1. the versioned JSON Schema;
2. valid/invalid conformance fixtures;
3. this compatibility policy.

They do not need to import Python package internals to decide whether their parser/validator conforms to spec v1.0.

## Migration policy

`interface-as-code migrate` provides deterministic migration behavior and refuses unsupported version paths.

A migration helper may only automate a change when the old document has enough information to produce the new contract without inventing business semantics. Otherwise the migration must stop with explicit guidance rather than guess ownership, recovery, monitoring or contract details.

For the current single specification line, migration from 1.0 to 1.0 is intentionally a deterministic no-op. The first breaking specification version must add its migration decision and fixtures in the same change as the new schema.

## Deprecation policy

A field or behavior cannot disappear from a supported spec version merely because the CLI no longer prefers it. Deprecation requires:

- release-note notice;
- replacement guidance when applicable;
- continued conformance for the supported version until a new breaking spec version is introduced.
