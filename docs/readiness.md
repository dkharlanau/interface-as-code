# Production-readiness checks

`interface-as-code check` evaluates deterministic operational policies after structural validation.

```bash
interface-as-code check examples/reference-landscape
interface-as-code check . --format json
interface-as-code check . --fail-on error
```

Policies cover ownership, retry/replay, idempotency, dead-letter handling, monitoring signals, business correlation, reconciliation, SLA, test intent, security and batch scheduling. Each finding includes severity, a stable code, the affected path, why it matters and remediation guidance.

The tool intentionally avoids a black-box AI readiness score. Teams can gate on explicit findings and review policy changes in Git.
