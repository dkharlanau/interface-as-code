# Enterprise interface domain model

Interface as Code models a **logical operational interface**: one producer-side business exchange with one contract and one set of delivery/recovery controls.

## When to use one specification

Keep consumers in one specification when they receive the same logical event/message/API contract and share materially the same delivery guarantee, replay policy, ownership and reconciliation intent. Use `interface.consumers` for fan-out.

## When to split specifications

Create separate specifications when a consumer has a different contract/version, delivery guarantee, independent retry/replay path, separate operational ownership, different reconciliation key/source of truth, or a separate lifecycle.

## Logical vs physical identity

`interface.id` identifies the logical operational interface. Runtime/deployment IDs belong in `route.external_ids`. DEV/QA/PROD endpoints should not create separate logical interfaces unless their operational contract materially differs.

## Core concepts

- `source`: logical provider/producer.
- `target`: primary consumer; retained as the v1.0 shorthand for one-to-one interfaces.
- `consumers`: optional fan-out consumers for one logical publication.
- `route`: middleware/hops and external catalog/runtime identifiers; descriptive, not executable.
- `lifecycle`: proposed, approved, active, deprecated, retired.
- `ownership`: business, technical and support accountability.
- `contract`: protocol/message/schema reference.
- `delivery` + `retry`: ordering, idempotency and recovery semantics.
- `monitoring`: operational signals and correlation key.
- `reconciliation`: business proof that source and target converged.
- `security`: references/expectations only; never secrets.

The reference landscape exercises REST request/response, SAP IDoc through middleware, event/Kafka publication, file/batch transfer and B2B/EDI.
