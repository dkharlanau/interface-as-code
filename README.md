# Interface as Code

**Git-native operational contracts and governance for enterprise integrations.**

OpenAPI/AsyncAPI can tell you what an API or message contract looks like. Interface as Code captures the operational questions that usually remain fragmented across Confluence, Excel, middleware, tickets and runbooks:

- Who owns this interface and its failures?
- Is replay safe and idempotent?
- Where do failed messages go?
- Which signals prove it is healthy?
- How do we reconcile source and target business data?
- Is the interface production-ready?
- What does a proposed change actually break?
- What does the full integration landscape look like?

## Working toolkit

```bash
python -m pip install -e ".[dev]"

interface-as-code init interfaces/customer --profile sap-idoc \
  --id CUSTOMER-MDG-S4-01 --name "Customer replication" \
  --source SAP-MDG --target SAP-S4
interface-as-code validate interfaces/
interface-as-code check interfaces/ --fail-on error
interface-as-code diff old/interface.yaml new/interface.yaml
interface-as-code catalog interfaces/ -o generated/catalog
```

The short `iac` command remains as a compatibility alias, while `interface-as-code` is the canonical public CLI name to avoid confusion with Infrastructure as Code.

## Bootstrap an existing Excel interface list

Export the sheet to CSV:

```bash
interface-as-code import-csv interface-list.csv interfaces/
```

The importer generates valid starter specs plus `import-report.json` listing every missing owner, support route, business key or system field as an explicit gap. It never silently invents operational facts.

## Reference landscape

`examples/reference-landscape/` contains an inventory for **30 synthetic enterprise interfaces** across SAP IDoc, REST, event/Kafka, file/batch and B2B/EDI. CI materializes and validates that portfolio. Tests also exercise 50-row inventory migration and 100-interface catalog generation.

## Model

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
```

## Typed composition instead of duplication

```yaml
contract:
  format: REST
  ref: {kind: openapi, uri: ./openapi.yaml}
mapping:
  ref: {kind: mapping-as-code, uri: ../mapping/customer.yaml, revision: v1}
reconciliation:
  key: customer_id
  frequency: daily
  source_of_truth: SAP-MDG
  ref: {kind: reconciliation-as-code, uri: ../controls/customer.yaml}
```

Local references and optional SHA-256 pins are checked deterministically. External HTTP/Git references are explicit but are not silently fetched during ordinary validation.

## Why not replace OpenAPI, AsyncAPI, Backstage, LeanIX or SAP Integration Assessment?

Those tools remain sources of truth for contracts, catalogs or technology decisions. Interface as Code focuses on the layer between design and operations: delivery semantics, recovery, ownership, monitoring, reconciliation, readiness and change impact.

## Documentation

- [Product strategy](PRODUCT.md)
- [Prioritized backlog](BACKLOG.md)
- [Domain model](docs/domain-model.md)
- [Excel/CSV migration](docs/migration-from-excel.md)
- [Readiness policies](docs/readiness.md)
- [Semantic diff](docs/semantic-diff.md)
- [Portfolio catalog](docs/catalog.md)
- [Typed references](docs/composition.md)

## Related projects

- [Mapping as Code](https://github.com/dkharlanau/mapping-as-code)
- [Reconciliation as Code](https://github.com/dkharlanau/reconciliation-as-code)
- [Transformation Graph](https://github.com/dkharlanau/transformation-graph)
- [Process as Code](https://github.com/dkharlanau/process-as-code)

## Status

**v0.2 P0 governance loop:** bootstrap → validate → readiness → semantic diff → catalog. Next depth is standards/SAP adapters, policy packs, observability, test generation, drift detection and MCP consumption.
