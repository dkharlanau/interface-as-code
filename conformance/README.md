# Interface as Code conformance suite

The conformance suite is a public specification contract. It intentionally does not import `interface_as_code` internals.

A third-party implementation can validate compatibility using only:

- the pinned JSON Schema under `spec/v<version>/interface.schema.json`;
- the valid/invalid fixtures under `conformance/v<version>/`;
- a JSON Schema 2020-12 implementation and YAML parser.

Reference run:

```bash
python conformance/run.py --spec-version 1.0
```

Machine-readable result:

```bash
python conformance/run.py --spec-version 1.0 --json
```

Conformance means that every fixture under `valid/` is accepted and every fixture under `invalid/` is rejected by the published schema. It does not require using the Python package or reproduce higher-level CLI readiness policies that intentionally live above the specification schema.

## Adding a specification version

A new breaking spec version must add, in the same change:

1. `spec/vX.Y/interface.schema.json`;
2. `conformance/vX.Y/valid/` representative fixtures;
3. `conformance/vX.Y/invalid/` boundary fixtures;
4. compatibility and migration guidance in `docs/versioning.md`;
5. deterministic migration support where an automatic migration is safe.

Do not overwrite an old published schema to make new fixtures pass. Old version directories are retained so implementers can pin compatibility.
