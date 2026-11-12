# A support handover brief, without a false sign-off

The next support team needs more than valid YAML. It needs to find who is named,
how to identify a business transaction, what recovery assumes, and which questions
remain unanswered. `handover` puts those concerns in one read-only brief. It reuses
the existing readiness policies, controls model and generated test plan; it does
not create another source of truth or run an integration.

```sh
interface-as-code handover examples/sap-mdg-to-s4-customer/interface.yaml
interface-as-code handover examples/rest-order-api/interface.yaml --format json
```

Both examples are synthetic. Their names and declared SAP details do not establish
universal IDoc, AIF, retry or delivery behavior. The asynchronous customer example
has a declared replay procedure. The synchronous API is a useful contrast; its
planned checks must not be treated as a permission to replay a live transaction.

## Start with the questions

The brief leads with built-in findings and a concrete question for each affected
contract path. Missing operational owner, support route, business correlation key,
replay guidance and reconciliation comparison are prioritized. Declared operational,
support, technical and business contacts appear together, with their source paths.
A declared name is not confirmation that the team accepted support responsibility.

Try a deliberately incomplete but structurally valid variant:

```sh
interface-as-code validate examples/governance/handover-gaps.yaml
# Exit 0: structurally valid.
interface-as-code handover examples/governance/handover-gaps.yaml --format markdown
# Exit 1: two readiness errors, plus warnings and information items.
```

The operational owner and support route are blank. The technical and business
contacts remain visible, so a reviewer can find the declared contact context
without reading YAML. The report does not assign the question to a person or
fabricate an answer. Three human-review prompts remain separate from the policy
finding counts: acceptance of support responsibility, replay authorization and
business-state checks, and evidence for this precise declaration.

The controls section is the existing `control_model` projection, including its
existing business-key fallback. The test-plan section is the existing
`generate_test_plan` output. A generated expected result such as “no duplicate
business state” is an expectation to test, not evidence that it passed.

## Bind the review to the declaration

JSON uses the additive report format `interface-as-code-handover/1.0`. It includes
the SHA-256 of the exact YAML bytes loaded and validated for this run. Changing
comments also changes that hash. It is not a Git commit ID, a signature, or a hash
of all referenced artifacts. Referenced mapping, contract, reconciliation and
evidence metadata are shown as declarations. Ordinary validation still checks
local references using the existing validator; no new HTTP fetch is performed.

For a before/after exercise, copy the synthetic asynchronous example directory,
change only `interface.target.system` in the copy to `SYNTHETIC-NEW-TARGET`, and
produce both JSON reports. The target and source hash must differ. Unchanged test
intent or evidence references do not authorize the new target: both reports keep
`acceptance.status: not_assessed`, `evidence_verification: not_performed`, and
`replay_authority: not_granted`. The existing semantic `diff` command is the right
next view for the declaration change. This brief does not compare observations or
create an evidence-invalidation registry.

## Exit behavior and scope

- Exit 0: the requested built-in finding threshold was not reached. Not a sign-off.
- Exit 1: the generated brief contains a finding at the requested threshold.
- Exit 2: invalid or unreadable input, or unsupported command arguments. No report.

The default threshold is `error`. `--fail-on warning`, `info` and `none` are
explicit alternatives. `none` still reports every finding, and never makes invalid
input acceptable. Human-review prompts are not counted as policy failures.

This first slice accepts one source contract. Overlays, custom policy packs,
observations, multi-contract catalogs and automatic output-file writing are not
supported by `handover`; unsupported options are rejected rather than ignored.
The existing commands for those workflows are unchanged. Output goes to stdout;
if saving it, use a separate destination, never redirect over an input or a
referenced file. Review internal metadata before sharing any generated brief.

No report creates replay authority, verifies a linked test run, approves a release
or changes the contract. Human review with independent interface-shaped cases is
still needed to evaluate handover friction, false alarms and whether questions
actually get answered. Automated synthetic checks do not substitute for those
observations.

## Review a changed target or mapping

Use `handover-diff` when the logical interface identity is unchanged but its
operational declaration changed:

```sh
interface-as-code handover-diff \
  examples/governance/handover-before.yaml \
  examples/governance/handover-after.yaml
# Exit 1: the target-system change reaches the default breaking threshold.
```

These synthetic files change the target system and mapping profile, while retaining
the declared owners, recovery approach and proposed tests. The report reuses the
existing semantic diff classifications, then shows four general review areas:
contacts, recovery, reconciliation and test intent. Unchanged values remain visible
because “the text did not change” does not mean “this team accepted a new target”
or “these checks ran against the new mapping.” It is a review checklist, not an
inferred dependency graph, proof of failure, or decision that every test must rerun.
The current handover brief follows the change summary in Markdown. JSON retains
both full briefs and both exact YAML hashes.

Two independent thresholds control the exit:

- `--fail-on-change` defaults to `breaking`, using existing semantic diff levels
  (`breaking`, `high-risk`, `review`, `informational`, `none`). Mapping-profile or
  mapping-reference changes retain the existing `review` classification. Choose
  `--fail-on-change review` if those should block your declaration-review gate.
- `--fail-on` defaults to `error`, using the current declaration's readiness
  findings (`error`, `warning`, `info`, `none`). Previous readiness findings remain
  in the report but are not counted as current failures.

Exit 1 means either requested threshold was reached. Exit 2 means one input is
invalid/unreadable or the interface IDs differ; no partial report is emitted.
Setting both thresholds to `none` still does not permit invalid input or transfer
approval. The JSON `gate` section states each threshold, its finding count, and
why the process returned its exit code. Exit 0 is never acceptance.

Only two explicit local contract files are accepted, not Git revision expressions.
Each is loaded once, and each hash binds those exact bytes. A comment-only edit
changes a hash without creating a semantic finding. Changes inside a referenced
file with an unchanged reference are **not compared**: the report explicitly keeps
`reference_content_comparison: not_performed`. Use the specialist artifact's
comparison and evidence workflow for those contents. This command neither fetches
remote evidence nor updates an evidence registry. It grants no replay authority.
