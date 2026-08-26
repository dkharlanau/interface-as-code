# Specification model

Interface as Code treats an enterprise interface as an operational contract, not only a message schema.

A useful interface specification must answer nine questions:

1. **Identity** — what interface is this?
2. **Endpoints** — which systems and business objects communicate?
3. **Trigger** — what starts the exchange?
4. **Contract** — what protocol/message/schema is used?
5. **Delivery** — what ordering and idempotency semantics are expected?
6. **Mapping** — where is transformation logic defined?
7. **Failure handling** — how is retry, replay, and dead-letter processing handled?
8. **Operations** — who owns the interface and where is it monitored?
9. **Reconciliation** — how do we prove that source and target converged?

## Canonical document

The canonical file is `interface.yaml`. It is validated against the JSON Schema shipped with the package and then against deterministic semantic rules.

```yaml
version: "1.0"
interface:
  id: CUSTOMER-MDG-S4-01
  name: Customer replication
  source: {system: SAP-MDG, object: BusinessPartner}
  target: {system: SAP-S4, object: Customer}
  mode: async

trigger:
  event: CustomerApproved

contract:
  format: IDoc
  message_type: DEBMAS

delivery:
  guarantee: at-least-once
  idempotency: {required: true, key: customer_id}

mapping:
  file: mapping.yaml

retry:
  strategy: manual

monitoring:
  owner: Customer Master Data Operations
  support_route: SAP AIF

reconciliation:
  key: customer_id
  frequency: daily
  source_of_truth: SAP-MDG
```

The schema intentionally avoids vendor-specific implementation fields unless they are needed to describe the contract. Vendor detail can live in references, mappings, fixtures, or generated adapters.

## Composition

An Interface as Code repository can reference adjacent machine-readable assets:

- **Mapping as Code** for field mapping and transformation rules.
- **Transformation Graph** for multi-step transformation lineage.
- **Reconciliation as Code** for detailed comparison controls.
- **Decision Tables as Code** for routing or validation rules.

The interface specification remains the entry point that connects these artifacts.
