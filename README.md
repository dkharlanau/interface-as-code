# Interface as Code

Versionable interface specifications covering contracts, mappings, retries, monitoring, ownership, reconciliation, and tests.

## Problem

Interface specifications are often fragmented across Confluence, Excel mapping sheets, sequence diagrams, tickets, and runbooks.

## Core idea

Define each interface as a structured, versionable specification covering contract, mapping, retry behavior, monitoring, ownership, and reconciliation.

## Example

```yaml
interface:
  id: CUSTOMER-OUT-01
  source: MDG
  target: S4
  mode: async

trigger:
  event: CustomerApproved

contract:
  format: IDoc
  message_type: DEBMAS

mapping:
  file: customer.mapping.yaml

retry:
  strategy: manual
  idempotent: true

monitoring:
  owner: Customer Operations

reconciliation:
  key: customer_id
```

## Initial scope

- canonical interface schema
- validation
- mapping references
- retry/idempotency definition
- ownership
- monitoring requirements
- reconciliation definition
- generated interface documentation
- sequence/data-flow diagrams
- test skeletons

## Long-term direction

Portable interface specifications that can produce documentation, tests, monitoring requirements, and agent context.

## Design principles

- versionable
- portable
- machine-readable
- deterministic-first
- visual where useful
- Git-friendly
- vendor-neutral where practical
- interoperable with enterprise tools

## Status

Planning.
