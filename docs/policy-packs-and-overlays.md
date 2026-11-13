# Policy packs and environment overlays

Policy packs change deterministic readiness policy configuration without copying rules into every interface.

```yaml
rules:
  security.classification-missing: {severity: error}
  evidence.missing: {enabled: false}
```

Environment overlays are intentionally limited to operational/environment metadata such as monitoring routes, runtime IDs, SLA and security expectations. They cannot rewrite the message contract.

```bash
interface-as-code check interface.yaml --policy policy-pack.yaml --overlay prod.overlay.yaml
interface-as-code explain interface.yaml --overlay prod.overlay.yaml
```

## Severity values and configuration errors

An explicitly supplied severity must be exactly error, warning or info.
Unknown spellings, uppercase forms, null, empty strings, booleans, numbers,
lists and objects are configuration errors, not a lower-severity finding.
The whole pack is checked before findings are processed, including unmatched
and disabled rules. Unknown rule identifiers are still allowed.

Omit severity to keep the original level. Explicit rule: false and enabled:
false still disable findings when the configuration is otherwise valid.
This deliberately tightens the previous behavior, which ignored false-like
severity values and could rank misspellings below every gate.

The standalone check command reports an invalid severity on stderr and exits 2
without a report, even with --fail-on none. This is a configuration check, not
an extra approval rule: valid warning/info overrides and explicit disable
mechanisms retain their original semantics. No unrelated policy fields are
newly validated by this bounded change.
