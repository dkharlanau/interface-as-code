# Operational generators

A validated interface can generate reviewable operational requirements without becoming an integration runtime.

```bash
interface-as-code controls interface.yaml
interface-as-code observability interface.yaml
interface-as-code test-plan interface.yaml
```

`controls` produces monitoring, recovery and reconciliation requirements. `observability` derives portable signal/correlation requirements and points to applicable OpenTelemetry convention families without freezing experimental conventions into the core schema. `test-plan` derives contract, duplicate/replay, retry/dead-letter, reconciliation and security scenarios. Pact references remain external contract-test sources of truth.
