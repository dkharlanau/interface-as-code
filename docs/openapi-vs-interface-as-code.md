# OpenAPI vs Interface as Code

OpenAPI is authoritative for an HTTP API contract: operations, parameters, schemas and responses. Interface as Code does not copy that model. It references OpenAPI and adds operational governance that usually lives elsewhere: ownership, retry/replay expectations, idempotency, monitoring responsibility, business reconciliation, lifecycle, service expectations and change-impact classification.

Use both: OpenAPI for the API contract; Interface as Code for the enterprise operational contract around it.
