# Read-only MCP server

The optional MCP v2 server exposes only the validated catalog index. It does not mutate specifications or call enterprise runtimes.

```bash
pip install 'interface-as-code[mcp]'
interface-as-code catalog interfaces -o generated/catalog
interface-as-code-mcp --catalog generated/catalog/index.json
```

Tools list/search/get validated interfaces and return source/catalog context. Invalid specifications never enter the catalog index.

## Threat model

The initial server has no write tools, no integration-runtime credentials, no arbitrary filesystem tool and no ability to replay messages. Treat the catalog as read-only published knowledge. Access control belongs to the MCP host/deployment boundary. If data is stale, regenerate from validated specs rather than letting an agent repair facts. Secrets and sensitive payload examples must never be placed in the catalog.

Recommended modes are local stdio or an authenticated read-only remote deployment. Execution against SAP, middleware, ticketing or monitoring systems belongs in separate controlled tools with explicit permissions.
