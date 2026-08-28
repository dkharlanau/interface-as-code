# Reference enterprise landscape

The checked-in `inventory.csv` describes 30 synthetic enterprise interfaces across SAP IDoc, REST, Kafka/event, CSV/file batch and B2B/EDI. It contains no customer data.

The purpose is not to make a large demo for its own sake. It gives the product one stable portfolio on which readiness, catalog, change and adapter behavior can be dogfooded release after release.

## Build the landscape

Materialize it with the same bootstrap path an enterprise would use for an existing interface inventory:

```bash
interface-as-code import-csv examples/reference-landscape/inventory.csv generated/reference-landscape
interface-as-code validate generated/reference-landscape
interface-as-code check generated/reference-landscape
interface-as-code catalog generated/reference-landscape -o generated/reference-catalog
```

The import, validation, readiness check and catalog build run in CI so every release is exercised against a portfolio rather than only single-file examples.

## Questions this landscape should answer

Use the reference portfolio to investigate concrete operational questions:

1. **What do we actually have?** Build the catalog and inspect systems, protocols, owners and support routes across the 30 interfaces.
2. **Where is the operational contract weak?** Run `check` across the generated landscape and inspect readiness findings instead of treating schema validity as production readiness.
3. **Which SAP boundaries are represented?** The fixture deliberately includes SAP MDG, S/4HANA, EWM and TM together with non-SAP applications and middleware-style boundaries.
4. **Who owns recovery?** Inspect the generated specs/catalog for `owner`, `support_route`, retry and reconciliation data rather than inferring support ownership from technology alone.
5. **What would a change actually alter?** Run the controlled before/after scenario below and review semantic severity instead of reading a raw YAML diff.
6. **Can the same source support other catalog views?** Use the generated interface specs as the input for Backstage, LeanIX and SAP-oriented projections rather than maintaining a second inventory.

## Controlled change scenario

`changes/customer-replication-before.yaml` and `changes/customer-replication-after.yaml` describe the same synthetic high-criticality customer replication interface before and after an intentionally weaker operational change.

```bash
interface-as-code diff \
  examples/reference-landscape/changes/customer-replication-before.yaml \
  examples/reference-landscape/changes/customer-replication-after.yaml
```

The after-state is still schema-valid, but it disables required idempotency for an at-least-once flow, reduces retry attempts, removes one monitoring signal and weakens recovery targets. Tests lock the important distinction:

- schema validity remains a structural question;
- semantic validation identifies the at-least-once/idempotency conflict;
- semantic diff classifies idempotency, retry and recovery-target changes as high-risk.

This scenario is intentionally synthetic and deterministic. It is evidence that the product can explain a controlled operational change; it is not evidence about any customer landscape.

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

## Evolution rule

Extend this fixture family instead of creating a parallel toy portfolio. New major capabilities should add or update at least one reference-landscape scenario when that capability is meaningful at portfolio scale.
