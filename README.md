# Interface as Code

**Git-native operational contracts and governance for enterprise integrations.**

API/message standards describe contracts well. Enterprise operations still need reliable answers to different questions: who owns an interface, whether replay is safe, what is monitored, how source and target are reconciled, whether a release is production-ready, what a change breaks, and whether documentation still matches reality.

Interface as Code makes those concerns versionable, deterministic and searchable.

## Current capabilities

```bash
# Create / migrate inventory
interface-as-code init interfaces/customer --profile sap-idoc --id CUSTOMER-01 --name "Customer replication"
interface-as-code import-csv interface-list.csv interfaces/
interface-as-code import-openapi openapi.yaml interfaces/order --id ORDER-API-01 --source Portal --target OMS
interface-as-code import-asyncapi asyncapi.yaml interfaces/order-event --id ORDER-EVENT-01 --source SAP-S4 --target Fulfillment

# Governance loop
interface-as-code validate interfaces/
interface-as-code check interfaces/ --fail-on error
interface-as-code diff HEAD~1:interfaces/customer/interface.yaml interfaces/customer/interface.yaml
interface-as-code catalog interfaces/ -o generated/catalog

# Generated operational artifacts
interface-as-code controls interfaces/customer/interface.yaml
interface-as-code observability interfaces/customer/interface.yaml
interface-as-code test-plan interfaces/customer/interface.yaml

# Enterprise adapters and runtime evidence
interface-as-code export backstage interfaces/customer/interface.yaml
interface-as-code export leanix interfaces/customer/interface.yaml
interface-as-code sap-summary interfaces/customer/interface.yaml
interface-as-code drift interfaces/customer/interface.yaml observed-evidence.yaml
```

`interface-as-code` is the canonical public command. `iac` remains a compatibility alias.

## Why this is useful

The product is deliberately not an integration runtime or a replacement for specialized standards. OpenAPI/AsyncAPI remain authoritative contract artifacts; Pact remains contract-test evidence; OpenTelemetry remains the telemetry semantic layer; Backstage/LeanIX remain catalogs; SAP tools remain design/runtime systems. Interface as Code links their relevant facts into one **operational contract** and adds deterministic governance around them.

The core loop is:

**bootstrap → validate → readiness → semantic diff → catalog → drift**

That loop becomes more valuable as a landscape grows from one interface to hundreds or thousands.

## Enterprise model

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
  lifecycle: active
ownership:
  business: Customer Master Data
  technical: SAP MDG Integration
  support: Customer Master Data Operations
contract:
  format: IDoc
  message_type: DEBMAS
delivery:
  guarantee: at-least-once
  idempotency: {required: true, key: customer_id}
retry:
  strategy: manual
  dead_letter: SAP AIF error queue
  replay: Reprocess after correction in the operational monitor.
monitoring:
  owner: Customer Master Data Operations
  support_route: SAP AIF
  business_key: customer_id
  signals: [technical_failure, business_validation_failure, processing_age]
reconciliation:
  key: customer_id
  frequency: daily
  source_of_truth: SAP-MDG
  comparison: Compare approved MDG customers with replicated S/4 customers.
profiles:
  sap:
    integration_style: process integration
    technology: IDoc
    aif_namespace: ZMDG
    aif_interface: CUSTOMER_OUT
```

## Typed composition

Specialized artifacts are referenced, not copied:

```yaml
contract:
  format: REST
  ref: {kind: openapi, uri: ./openapi.yaml}
mapping:
  ref: {kind: mapping-as-code, uri: ../mapping/customer.yaml, revision: v1}
```

Local refs and optional SHA-256 pins are validated deterministically. External Git/HTTP refs remain explicit and are not silently fetched during ordinary validation.

## Portfolio-scale dogfooding

`examples/reference-landscape/inventory.csv` contains 30 synthetic enterprise interfaces. Tests also cover 50-row inventory migration and 100-interface catalog builds. The reproducible benchmark currently records roughly 0.17 s / 1.73 s / 15.56 s for 50 / 500 / 5,000 catalog entries on the development container; see [performance baseline](docs/performance.md).

## Read-only MCP

An optional MCP v2 server exposes only the validated catalog index:

```bash
pip install 'interface-as-code[mcp]'
interface-as-code catalog interfaces -o generated/catalog
interface-as-code-mcp --catalog generated/catalog/index.json
```

It can list/search/read interface context but cannot modify specs or execute enterprise integrations.

## Documentation

- [Product strategy](PRODUCT.md) · [Backlog](BACKLOG.md)
- [Domain model](docs/domain-model.md) · [Specification](docs/specification.md) · [Versioning](docs/versioning.md)
- [Excel/CSV migration](docs/migration-from-excel.md) · [Standards interoperability](docs/standards-interoperability.md)
- [Production readiness](docs/readiness.md) · [Semantic diff](docs/semantic-diff.md) · [Drift](docs/drift.md)
- [Operational generators](docs/operational-generators.md) · [Security](docs/security.md)
- [Catalog](docs/catalog.md) · [Catalog adapters](docs/catalog-adapters.md) · [SAP profile](docs/sap-profile.md)
- [Policy packs / overlays](docs/policy-packs-and-overlays.md) · [MCP](docs/mcp.md)

## Stable specification artifact

Specification v1.0 is published in-repository at [`spec/v1.0/interface.schema.json`](spec/v1.0/interface.schema.json). The CLI/package version evolves independently from the spec version.

## Related projects

- [Mapping as Code](https://github.com/dkharlanau/mapping-as-code)
- [Reconciliation as Code](https://github.com/dkharlanau/reconciliation-as-code)
- [Transformation Graph](https://github.com/dkharlanau/transformation-graph)
- [Process as Code](https://github.com/dkharlanau/process-as-code)

## Status

**v0.3:** the deterministic operational-governance core, standards import, enterprise adapters, drift and read-only agent surface are implemented. Distribution/search polish and deeper live vendor integrations remain intentionally separate from the core.
