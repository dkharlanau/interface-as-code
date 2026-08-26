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
