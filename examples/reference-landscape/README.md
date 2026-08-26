# Reference enterprise landscape

The checked-in `inventory.csv` describes 30 synthetic enterprise interfaces across SAP IDoc, REST, Kafka/event, CSV/file batch and B2B/EDI. It contains no customer data.

Materialize the landscape with the same bootstrap path an enterprise would use for an existing interface inventory:

```bash
interface-as-code import-csv examples/reference-landscape/inventory.csv generated/reference-landscape
interface-as-code validate generated/reference-landscape
interface-as-code check generated/reference-landscape
interface-as-code catalog generated/reference-landscape -o generated/reference-catalog
```

This is executed in CI so every release is dogfooded against a portfolio rather than only single-file examples.
