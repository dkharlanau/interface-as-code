# Specification and tool versioning

The specification version and CLI/package version evolve independently.

- `interface.yaml version: "1.0"` selects the v1.0 specification contract.
- Python package/CLI releases use semantic versioning independently.
- The versioned schema lives under `spec/v1.0/interface.schema.json` and is packaged for offline validation.
- Backward-compatible optional fields may be added without changing the major specification version.
- Breaking specification changes require a new schema directory, migration guidance and conformance fixtures.

`interface-as-code migrate` provides deterministic migration behavior and refuses unsupported version paths. Third-party implementations can validate directly against the JSON Schema without importing Python internals.
