# Contributing

Contributions should improve a concrete enterprise integration workflow and remain deterministic by default.

1. Add or update a realistic fixture/reference-landscape scenario.
2. Add tests for validation, generated output or compatibility behavior.
3. Run `pytest -q`, `interface-as-code validate examples`, and the relevant CLI command.
4. Do not add credentials, customer payloads or proprietary project data.
5. Prefer adapters/references to copying external standards into the core schema.

Breaking specification changes require a new versioned schema, migration guidance and conformance fixtures.
