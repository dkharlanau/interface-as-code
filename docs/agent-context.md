# Agent context

The same specification that humans review can be used as bounded context for coding and operations agents.

An agent can answer questions such as:

- Which system is the source of truth?
- Is replay safe?
- Which key should be used for correlation?
- Who owns a failure?
- Where should an error be monitored?
- Which mapping artifact applies?
- How can source and target be reconciled?

## Recommended agent boundary

Expose the validated specification, generated documentation, and linked artifacts as read-only context. Keep execution permissions separate.

A safe sequence is:

1. validate the specification deterministically;
2. resolve linked mapping/reconciliation artifacts;
3. provide the resulting context to the agent;
4. let the agent propose an action;
5. execute through controlled enterprise tooling;
6. record evidence back into the operational system.

Interface as Code therefore acts as a machine-readable control plane for knowledge about an interface, not as an unrestricted integration runtime.
