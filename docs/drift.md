# Specification drift

`interface-as-code drift` compares declared paths with source-attributed design/runtime evidence. Evidence contains path, observed value, source, timestamp and status. Unavailable or stale evidence is distinct from actual drift, and the command never edits the canonical specification.

```bash
interface-as-code drift interface.yaml evidence.yaml --fail-on-drift
```
