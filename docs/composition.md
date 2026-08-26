# Artifact composition and typed references

Interface as Code does not duplicate specialized specifications. It links them through typed references.

```yaml
mapping:
  ref:
    kind: mapping-as-code
    uri: ../mapping/customer.mapping.yaml
    revision: v1
    sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
```

Supported kinds include Mapping as Code, Reconciliation as Code, Transformation Graph, OpenAPI, AsyncAPI, Pact, evidence and custom artifacts.

Local paths are resolved during validation. An optional SHA-256 pin makes the reference tamper-evident. HTTP(S)/Git references are preserved as explicit external references and are not silently downloaded by ordinary validation. This keeps validation deterministic.
