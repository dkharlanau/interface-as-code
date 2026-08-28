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

## Build the review set

For a stronger end-to-end proof, build the retained reference-landscape review bundle:

```bash
python scripts/build_reference_landscape_review.py \
  --output build/reference-landscape-review \
  --force
```

The review builder must prove all of the following in one run:

- 30 inventory rows produce 30 unique interface contracts without source-import gaps;
- every generated contract passes structural validation;
- readiness has no error-level findings, while unresolved operational warnings remain visible rather than being silently treated as production-ready;
- the generated catalog contains the full landscape and topology;
- one representative contract for each of the five integration styles produces operational controls/reconciliation, observability, a test plan, Backstage and LeanIX projections, plus a SAP summary where relevant;
- a target-system topology change is classified as a breaking semantic change;
- a synthetic observed-evidence fixture proves both `match` and `drift` behavior.

CI retains the complete bundle for 90 days, including generated specs, catalog, readiness report, semantic-diff fixture, drift fixture and representative projections.

## Evidence boundary

The landscape is deliberately **synthetic implementation proof**, not a claim that 30 production interfaces have been governed with this tool.

Imported contracts remain lifecycle `proposed`. Warnings such as missing replay detail, incomplete reconciliation comparison, SLA gaps or missing tests are useful output: they show what the source inventory does not yet prove.

The next maturity gate is independent practitioner review/use of this landscape or an equivalent real-world inventory. Adding more synthetic rows alone would not make the product more validated.