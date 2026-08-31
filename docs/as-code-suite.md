# Interface as Code in the as-code suite

Interface as Code owns the operational integration contract: endpoints, trigger, payload contract, delivery guarantees, retry, monitoring, ownership, reconciliation expectations, security, tests, and lifecycle.

## Typed mapping and reconciliation references

The v1.0 schema supports explicit artifact references without embedding another product's domain model:

```yaml
mapping:
  profile: customer-core
  ref:
    kind: mapping-as-code
    uri: mappings/customer-master.yaml
    revision: main@<immutable-commit>
    sha256: <canonical-mapping-sha256>

reconciliation:
  key: customer_id
  frequency: daily
  source_of_truth: SAP-MDG
  comparison: Compare approved customers with replicated target customers.
  ref:
    kind: reconciliation-as-code
    uri: controls/customer-reconciliation.yaml
    revision: main@<immutable-commit>
    sha256: <reconciliation-file-sha256>
```

Interface validation checks the reference shape and SHA syntax. It does not fetch, validate, or execute the foreign artifact during ordinary validation.

Mapping as Code can generate the mapping binding after comparing source and target endpoints:

```bash
map-code bind-interface interface.yaml mapping.yaml \
  --mapping-uri mappings/customer-master.yaml \
  --revision main@COMMIT_SHA \
  --output interface.bound.yaml
```

## Related projects

- [Mapping as Code](https://github.com/dkharlanau/mapping-as-code) owns field transformations and provides the tested `bind-interface` handoff.
- [Reconciliation as Code](https://github.com/dkharlanau/reconciliation-as-code) owns executable source-to-target controls and evidence. An Interface as Code `reconciliation.ref` is traceability, not execution.
- [Process as Code](https://github.com/dkharlanau/process-as-code) can reference an interface from the business step that invokes it and resolve nested artifacts with explicit network authority.
- [Decision Tables as Code](https://github.com/dkharlanau/decision-tables-as-code) can govern routing or classification decisions used around an interface; no automatic binding is currently implemented.

## Handoff rule

Keep foreign artifacts referenced and immutable. Readiness still requires operational details and evidence in the interface contract; a valid mapping or reconciliation reference does not prove the interface can be supported in production.
