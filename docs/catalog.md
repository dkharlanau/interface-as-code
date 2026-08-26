# Multi-interface catalog

```bash
interface-as-code catalog interfaces/ -o generated/catalog
# Build a scoped topology/catalog to avoid portfolio hairballs:
interface-as-code catalog interfaces/ -o generated/sap-catalog --system SAP-S4
interface-as-code catalog interfaces/ -o generated/critical-idoc --protocol IDoc --criticality critical
```

The command creates `index.html` (serverless searchable catalog), `index.json` (machine-readable portfolio index), `topology.mmd` (Mermaid graph), and `interfaces/<ID>.html` detail pages with readiness findings.

Invalid specifications are isolated in the report rather than corrupting the whole build. Tests exercise 100-interface catalog generation.

CLI filters (`--system`, `--protocol`, `--owner`, `--criticality`) are applied before topology generation, so teams can create focused graphs for one system or operational slice instead of an unreadable full-landscape hairball.
