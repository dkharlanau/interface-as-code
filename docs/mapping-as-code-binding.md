# Binding a Mapping as Code contract

Interface as Code owns the operational interface contract: trigger, transport contract, delivery guarantee, retry, monitoring, reconciliation, security, and lifecycle.

Mapping as Code owns field-level transformation intent. The two contracts should be linked rather than duplicated.

## Official artifact reference

Interface as Code v1.0 already supports a mapping artifact reference:

```yaml
mapping:
  profile: legacy-customer-to-s4-business-partner
  ref:
    kind: mapping-as-code
    uri: mappings/customer-master.yaml
    revision: main@abc123
    sha256: <canonical-mapping-sha256>
```

`sha256` is the canonical Mapping as Code document hash, so a retained interface contract can identify the exact mapping semantics it was reviewed against even when YAML formatting changes.

## Generate the binding

From the Mapping as Code repository/tool:

```bash
map-code bind-interface \
  interface.yaml \
  mapping.yaml \
  --mapping-uri mappings/customer-master.yaml \
  --revision main@abc123 \
  -o interface.bound.yaml
```

The command does not generate or infer interface delivery semantics. It updates only the official `mapping.ref` artifact reference and, when missing, the mapping profile.

## Endpoint safety

Before binding, the tool compares the declared source/target system and object in both contracts.

A mismatch fails by default. This prevents a valid mapping artifact from being attached to an unrelated interface merely because the file path was wrong.

An explicit `--allow-endpoint-mismatch` exists for controlled exceptions, such as a deliberately broader interface contract, but should not be the normal path.

## Contract conformance

Mapping as Code retains the Interface as Code v1.0 JSON Schema and its source blob SHA in its conformance suite. Generated bound interfaces are validated against that retained contract in CI.

This makes the integration directional and explicit:

```text
Interface as Code
  owns runtime/interface semantics
        │
        └── mapping.ref(kind=mapping-as-code, uri, revision, sha256)
                         │
                         ▼
                  Mapping as Code
                  owns field mappings
```

Neither repository needs to copy the other's domain model.
