# Catalog adapters

Interface as Code remains the Git-versioned operational source. Enterprise catalogs receive summaries and stable IDs, not a duplicate technical contract.

```bash
interface-as-code export backstage interface.yaml
interface-as-code export leanix interface.yaml
```

| Data | System of record |
| --- | --- |
| Contract, delivery, retry/replay, reconciliation, readiness | Interface as Code / linked artifact |
| Stable interface ID | Interface as Code |
| Technical/runtime external IDs | referenced runtime/catalog system |
| Enterprise capability/application taxonomy | enterprise catalog |
| Catalog display/enrichment metadata | enterprise catalog |

The Backstage adapter emits a `Resource`. The LeanIX adapter emits a neutral interface payload. Inbound LeanIX data is treated as comparison evidence, never blindly merged into the richer operational contract.
