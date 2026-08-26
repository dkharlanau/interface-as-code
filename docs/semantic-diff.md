# Semantic interface diff

Raw YAML diff cannot tell reviewers whether a change alters production behavior.

```bash
interface-as-code diff old/interface.yaml new/interface.yaml
interface-as-code diff old.yaml new.yaml --format json --fail-on high-risk
```

Changes are classified as **breaking**, **high-risk**, **review**, or **informational** based on the operational concern affected. Classification is deterministic and versioned with the tool.
