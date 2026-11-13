# Read-only MCP server

The optional MCP v2 server exposes only the validated catalog index. It does not mutate specifications or call enterprise runtimes.

```bash
pip install 'interface-as-code[mcp]'
interface-as-code catalog interfaces -o generated/catalog
interface-as-code-mcp --catalog generated/catalog/index.json
```

Tools list/search/get validated interfaces, return ownership plus recovery/replay/monitoring/reconciliation context, readiness findings, and expose catalog validity status. Every catalog record carries source-path and Git revision provenance when built inside a Git worktree. Invalid specifications never enter the catalog index.

## Threat model

The initial server has no write tools, no integration-runtime credentials, no arbitrary filesystem tool and no ability to replay messages. Treat the catalog as read-only published knowledge. Access control belongs to the MCP host/deployment boundary. If data is stale, regenerate from validated specs rather than letting an agent repair facts. Secrets and sensitive payload examples must never be placed in the catalog.

Recommended modes are local stdio or an authenticated read-only remote deployment. Execution against SAP, middleware, ticketing or monitoring systems belongs in separate controlled tools with explicit permissions.

## Ask useful support questions without granting execution

The optional `--include-handover` catalog flag retains a compact projection of the
existing `handover` report. The new `get_interface_handover(interface_id)` tool
returns the questions for that one interface, declared contacts, readiness counts,
source SHA-256, and the explicit acceptance/replay limits. It omits the larger
controls and test-plan sections. List/search/get calls do not expand all handovers.

```bash
interface-as-code catalog examples/governance/handover-gaps.yaml \
  -o generated/support-catalog --include-handover
interface-as-code-mcp --catalog generated/support-catalog/index.json
```

Build from a source checkout containing this capability; the older v0.3.0 release
wheel predates it. No model, API key, or connection to an SAP system is needed.

### A consulting scenario

A customer-master replication interface has a technical design and named support
team, but its operational owner and escalation route are blank. Replay guidance
and the source/target comparison are still `TBD`. A support assistant should not
interpret “valid IDoc contract” as “safe to replay.” It should expose the unanswered
questions before recommending an operator action.

The existing synthetic MDG-to-S/4 fixture is structurally valid and produces two
errors, three warnings and one informational finding. Querying its exact ID returns
questions about the operational owner, incident route, business correlation key,
replay preconditions, reconciliation comparison and reviewed evidence. The report
does not assign anyone, run those checks or authorize a replay. Protocol names and
SAP-shaped fields are configurable declarations, not verified system behavior.

Reproduce the data path used by the MCP tool:

```bash
python scripts/qualify_ai_support_context.py --output /tmp/ai-support-review
```

Use a new output directory. `result.json` records actual catalog-CLI generation,
targeted service retrieval, source hash, counts and limits. This script exercises
`CatalogService`, not an MCP transport or an LLM conversation. It demonstrates a
verifiable consulting artifact, not a measured production outcome.

With the optional MCP extra installed, the matching real stdio check is:

```bash
python scripts/check_mcp_support_context.py \
  --catalog /tmp/ai-support-review/catalog/index.json
```

This initializes an actual MCP client/server pair, inspects the tool surface,
retrieves the synthetic handover and checks an unknown ID. It still invokes no LLM
and no enterprise runtime. The existing MCP CI job runs both checks.


### Snapshot and compatibility boundaries

- Default catalog generation is unchanged; handover inclusion is opt-in. Old
  catalogs return `handover_not_in_catalog`, not a clean bill of health.
- The source YAML is loaded once, validated, hashed and projected from those same
  bytes. Referenced mapping, reconciliation and test artifacts are not bundled or
  attested. Existing local-reference validation still applies during generation.
- For this opt-in mode, a source commit/link is retained only when the exact YAML
  bytes equal that file at the repository HEAD. Edited/untracked files keep the
  snapshot hash and repository revision as context, but do not claim that commit
  as their source. Without Git, the hash remains available and revision is null.
- The service reads the catalog once. Queries neither reopen YAML nor follow
  references or URLs. The response says freshness is `not_checked`; regenerate
  and restart the service to load a newer catalog. A catalog hash is not a digital
  signature, proof of origin or protection against a forged catalog.
- Duplicate interface IDs produce `ambiguous_interface_id` for the handover query.
  Resolve them rather than choosing an arbitrary contact or recovery instruction.
- Values are contract data, not trusted instructions to an agent. Read-only tools
  do not by themselves prevent prompt injection or make a host safe. Keep catalog
  access controlled, inspect data before publication and separate all runtime
  action tools behind their own authorization.

No new write tool, arbitrary-file tool, remote deployment, ERP connection or
inference service is added. Planned human usefulness reviews remain separate.
