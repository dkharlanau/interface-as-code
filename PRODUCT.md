# Product strategy

## Vision

Make every enterprise interface reviewable, testable, operable, and discoverable from one version-controlled operational contract.

Interface as Code is not another API description language and not an integration runtime. It is the missing operational layer around an interface: ownership, delivery semantics, replay safety, mappings, monitoring, reconciliation, lifecycle, risk, and evidence.

## North-star question

Given any interface, a human or tool should be able to answer in under a minute:

1. What business exchange does this interface implement?
2. Which systems, objects, providers, and consumers participate?
3. Which technical contract describes the payload/API/event?
4. What delivery guarantees and ordering assumptions apply?
5. Is retry/replay safe and how is it performed?
6. Who owns failures and where are they observed?
7. How is business-level convergence proven?
8. What data/security constraints apply?
9. What changes would be breaking or operationally risky?
10. Which evidence proves that the interface is production-ready?

## Primary users

- integration architects
- SAP integration and functional consultants
- API/platform teams
- enterprise architects
- support/AMS teams
- migration and transformation teams
- developers and AI agents that need reliable bounded interface context

## Positioning

Interface as Code complements rather than replaces specialized standards and platforms:

- OpenAPI: HTTP API contract
- AsyncAPI: event/message API contract
- Arazzo: API workflows
- OpenAPI Overlay: deterministic OpenAPI transformations
- CloudEvents: portable event envelope
- OpenTelemetry: telemetry conventions
- Pact: consumer/provider contract testing
- Backstage / SAP LeanIX: enterprise/software catalogs
- SAP Integration Assessment: integration technology guidance

The product's differentiated layer is the operational contract and governance workflow that connects design-time contracts to production ownership, recoverability, observability, reconciliation, and change control.

## Core product loops

### 1. Bootstrap
Create a useful specification from a template or import existing metadata from OpenAPI, AsyncAPI, CSV/Excel inventories, SAP artifacts, or enterprise catalogs.

### 2. Validate readiness
Run deterministic schema, semantic, policy, security, observability, replay-safety, and reconciliation checks. Produce actionable findings rather than only pass/fail.

### 3. Review change
Compare two interface versions and classify contract, topology, delivery, ownership, security, and operational changes by impact.

### 4. Publish and discover
Generate human documentation, Mermaid topology, portfolio catalogs, machine context, and catalog adapters from the validated source.

### 5. Verify reality
Compare declared specifications with available design-time/runtime metadata and surface drift.

### 6. Operate and automate
Generate monitoring requirements, runbook sections, reconciliation controls, test skeletons, and safe agent context.

## Product principles

- deterministic core; AI may explain but does not decide conformance
- reference specialized standards instead of duplicating them
- useful with one interface, more valuable with hundreds
- no mandatory SAP/BTP/cloud dependency
- local-first and CI-friendly
- vendor-neutral core with explicit vendor profiles
- every field should support a decision, control, generated artifact, or searchable relation
- no documentation-only fields without a clear consumer

## Success metrics

A release is valuable when it reduces real interface work. Track:

- time to bootstrap a specification for an existing interface
- percentage of production-readiness checks automatically evaluable
- number of supported import/export adapters
- percentage of changes classified automatically by `diff`
- number of interfaces handled in one catalog build
- number of generated operational artifacts used without manual rewriting
- installation/use of the CLI and GitHub Action
- external stars, forks, issues, package downloads, and inbound links

## Product sequence

1. Make adoption fast: `init`, imports, examples, distribution.
2. Make the specification enforce useful operational controls: readiness policies.
3. Make change review indispensable: semantic diff and PR checks.
4. Make the product scale to portfolios: catalog, topology, reporting.
5. Connect enterprise ecosystems: SAP, Backstage, LeanIX, OpenTelemetry, Pact.
6. Add drift detection and agent/MCP access after the deterministic foundation is strong.
