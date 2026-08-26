# Product backlog

Priorities are based on product value, adoption friction, and differentiation — not implementation novelty.

## P0 — Make it genuinely useful

| Issue | Outcome |
| --- | --- |
| #4 | stabilize enterprise interface identity, lifecycle, provider/consumer, route, and ownership model |
| #1 | typed references and deterministic artifact resolution |
| #5 | `iac init` profiles so first-time users do not need to learn the schema |
| #6 | bulk bootstrap from CSV/Excel interface inventories |
| #7 | production-readiness policies and explainable findings |
| #8 | semantic change-impact / breaking-change diff |
| #9 | multi-interface catalog, topology, and portfolio report |
| #10 | reusable GitHub Action and PR policy gate |
| #21 | realistic 25–50 interface reference landscape used for dogfooding |
| #19 | installability, docs, search/discoverability, stable schemas, and distribution |

### P0 release sequence

1. **Adoption foundation** — #4, #1, #5, #6, #21
2. **Governance loop** — #7, #8, #10
3. **Portfolio value** — #9
4. **Distribution and discovery** — #19 runs continuously, but meaningful promotion starts after the governance loop is demonstrable

## P1 — Enterprise depth and interoperability

| Issue | Outcome |
| --- | --- |
| #2 | import/link OpenAPI and AsyncAPI contract metadata; document Arazzo/Overlay/CloudEvents boundary |
| #3 | generate operational controls and SAP profile foundations |
| #11 | organization policy packs and environment overlays |
| #12 | security/privacy/data-handling controls |
| #13 | portable observability requirements aligned with OpenTelemetry conventions |
| #14 | contract/replay/reconciliation test plans and adapters, including Pact integration |
| #15 | Backstage and SAP LeanIX catalog adapters |
| #16 | SAP Integration Suite / Integration Assessment bridge |
| #17 | drift detection between declared specification and observed evidence |
| #20 | specification versioning, compatibility policy, and conformance suite |

## P2 — Agent consumption

| Issue | Outcome |
| --- | --- |
| #18 | read-only MCP server over validated interface catalogs |

MCP stays behind the deterministic product foundation. An agent interface is useful only after validation, readiness, diff, catalog, and provenance are trustworthy.

## Product bets

### Bet 1 — Readiness review is the wedge

The fastest route to repeat value is not documentation generation. It is catching missing ownership, unsafe replay, weak monitoring, absent reconciliation, and other go-live risks deterministically.

### Bet 2 — Semantic diff can become the daily habit

Raw YAML diff is easy to copy. A reliable explanation of what an interface change means operationally is much harder and more valuable.

### Bet 3 — Portfolio catalog creates compounding value

A single spec is useful. Hundreds of validated specs become an enterprise integration inventory that can be searched, analyzed, exported, and queried.

### Bet 4 — Existing standards are inputs, not competitors

OpenAPI, AsyncAPI, Arazzo, OpenAPI Overlay, CloudEvents, Pact, OpenTelemetry, Backstage, LeanIX, and SAP Integration Assessment should remain authoritative for their specialized concerns. Interface as Code links them into an operational governance contract.

### Bet 5 — SAP is the credibility profile, not the core

SAP examples and adapters provide difficult, realistic enterprise scenarios while the canonical model stays vendor-neutral and usable without SAP access.

## Not now

Do not prioritize:

- an integration runtime/execution engine
- a low-code flow designer
- generated integration implementation code
- a hosted SaaS control plane
- AI-based validity decisions
- deep vendor dashboard generation before portable observability semantics exist
- unrestricted agent execution against production systems

These directions would expand surface area before the core product proves value.
