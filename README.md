# Interface as Code

A versionable, machine-readable way to describe **how an enterprise interface behaves in production** — contract, mapping, delivery semantics, retry, monitoring, ownership, reconciliation, and tests.

Interface documentation is usually fragmented across Confluence pages, Excel mapping files, integration middleware, tickets, diagrams, and runbooks. That makes it difficult to answer basic operational questions reliably: *What is the source of truth? Is replay safe? Who owns a failure? How do we prove the target caught up?*

Interface as Code puts those answers in one validated specification and provides a foundation for enterprise integration governance in Git.

## What is implemented

This repository now contains a working v0.1 core:

- canonical YAML specification
- JSON Schema validation
- deterministic semantic validation
- CLI: `iac validate` and `iac render`
- generated Markdown and Mermaid views
- SAP IDoc example: MDG → S/4HANA customer replication
- vendor-neutral REST API example
- pytest coverage
- GitHub Actions validation

Product direction is tracked in [PRODUCT.md](PRODUCT.md). The prioritized implementation backlog is in [BACKLOG.md](BACKLOG.md) and GitHub Issues.

## Example

```yaml
version: "1.0"

interface:
  id: CUSTOMER-MDG-S4-01
  name: Customer replication from SAP MDG to S/4HANA
  source: {system: SAP-MDG, object: BusinessPartner}
  target: {system: SAP-S4, object: Customer}
  mode: async
  pattern: message-driven
  criticality: high

trigger:
  event: CustomerApproved

contract:
  format: IDoc
  message_type: DEBMAS
  basic_type: DEBMAS07

delivery:
  guarantee: at-least-once
  ordering: per-key
  idempotency:
    required: true
    key: customer_id

mapping:
  file: mapping.yaml

retry:
  strategy: manual
  dead_letter: SAP AIF error queue

monitoring:
  owner: Customer Master Data Operations
  support_route: SAP AIF

reconciliation:
  key: customer_id
  frequency: daily
  source_of_truth: SAP-MDG
```

## Quick start

```bash
python -m pip install -e ".[dev]"

iac validate examples/sap-mdg-to-s4-customer/interface.yaml

iac render examples/sap-mdg-to-s4-customer/interface.yaml \
  -o generated/customer-interface.md

pytest -q
```

Render only the sequence diagram:

```bash
iac render examples/sap-mdg-to-s4-customer/interface.yaml --format mermaid
```

## Why this is different from OpenAPI or AsyncAPI

OpenAPI and AsyncAPI are excellent contract formats. Interface as Code targets the layer around the contract that enterprise delivery and operations still have to manage:

| Concern | Interface as Code |
| --- | --- |
| Message/API contract | referenced or summarized |
| Field mapping | linked artifact |
| Retry/replay policy | explicit |
| Idempotency | explicit |
| Monitoring ownership | explicit |
| Business reconciliation | explicit |
| Test intent | explicit |
| Human documentation | generated |
| Agent context | generated from validated source |

It is designed to complement existing interface-description standards, not replace them.

## Repository layout

```text
.
├── docs/
│   ├── agent-context.md
│   ├── specification.md
│   └── validation.md
├── examples/
│   ├── rest-order-api/
│   └── sap-mdg-to-s4-customer/
├── src/interface_as_code/
│   ├── schemas/interface.schema.json
│   ├── cli.py
│   ├── loader.py
│   ├── renderer.py
│   └── validator.py
├── tests/
├── BACKLOG.md
├── PRODUCT.md
├── pyproject.toml
└── ROADMAP.md
```

## Design principles

- deterministic validation first
- Git-friendly and diffable
- portable across integration technologies
- operational semantics are first-class
- business reconciliation is part of the interface definition
- references instead of duplicating specialized models
- machine-readable enough for agents, readable enough for reviews

## Related projects

- [Mapping as Code](https://github.com/dkharlanau/mapping-as-code)
- [Transformation Graph](https://github.com/dkharlanau/transformation-graph)
- [Reconciliation as Code](https://github.com/dkharlanau/reconciliation-as-code)
- [Process as Code](https://github.com/dkharlanau/process-as-code)
- [Enterprise Change Graph](https://github.com/dkharlanau/enterprise-change-graph)
- [Decision Tables as Code](https://github.com/dkharlanau/decision-tables-as-code)
- [Data Relationship Map](https://github.com/dkharlanau/data-relationship-map)
- [Cutover Graph](https://github.com/dkharlanau/cutover-graph)
- [Project Evidence Graph](https://github.com/dkharlanau/project-evidence-graph)

## Status

**v0.1 core implemented.** Current P0 work focuses on enterprise model stabilization, fast bootstrap from templates/CSV, production-readiness policies, semantic change impact, portfolio catalog generation, and CI adoption.
