# Validation rules

Validation has two layers.

## 1. Structural validation

The JSON Schema checks required sections, allowed values, identifiers, and object shapes.

Examples:

- `version` must be `1.0`.
- `interface.id` must be stable and Git-friendly.
- `interface.mode` is one of `sync`, `async`, or `batch`.
- monitoring and reconciliation are mandatory.
- unknown top-level fields fail validation to prevent silent specification drift.

## 2. Semantic validation

Some risks cannot be represented cleanly by schema alone. The CLI therefore runs deterministic semantic checks.

Current rules:

| Rule | Why |
| --- | --- |
| Async interfaces require retry behavior | asynchronous failure must have an explicit recovery path |
| IDoc contracts require `message_type` | `IDoc` alone is not a usable contract |
| Automatic retry requires `max_attempts` | avoids unbounded retry loops |
| At-least-once delivery requires idempotency | duplicate delivery is expected behavior |
| Monitoring requires an owner | every failure needs an accountable operational team |
| Reconciliation requires a business key | technical success alone does not prove data convergence |
| Referenced mapping files must exist | prevents documentation from pointing to missing logic |
| Local contract schema references must exist | catches broken OpenAPI/schema links before merge |
| Referenced test fixtures must exist | keeps declared tests reproducible |

The validator should remain deterministic. AI can explain or propose fixes, but should not decide whether a specification is valid.
