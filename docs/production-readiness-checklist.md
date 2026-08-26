# Integration production-readiness checklist

Before go-live, check deterministic questions rather than relying on a generic score: Is there an accountable owner? Can an async failure be recovered? Is at-least-once delivery idempotent? Where are dead messages retained? Which technical and business signals are monitored? How is a transaction correlated? How does source/target reconciliation work? Is the recovery target explicit? Are security expectations defined? Are happy-path, duplicate/replay and failure tests represented?

`interface-as-code check` turns these questions into versioned policy findings.
