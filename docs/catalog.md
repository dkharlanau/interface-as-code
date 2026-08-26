# Multi-interface catalog

```bash
interface-as-code catalog interfaces/ -o generated/catalog
```

The command creates `index.html` (serverless searchable catalog), `index.json` (machine-readable portfolio index), `topology.mmd` (Mermaid graph), and `interfaces/<ID>.html` detail pages with readiness findings.

Invalid specifications are isolated in the report rather than corrupting the whole build. Tests exercise 100-interface catalog generation.
