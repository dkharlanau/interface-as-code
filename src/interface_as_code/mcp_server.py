from __future__ import annotations
import argparse, os
from .catalog_service import CatalogService


def create_server(catalog_path: str):
    try:
        from mcp.server import MCPServer
    except ImportError as exc:
        raise RuntimeError("Install Interface as Code with the 'mcp' extra to run the MCP server.") from exc
    service=CatalogService(catalog_path)
    server=MCPServer("interface-as-code")

    @server.tool()
    def list_interfaces() -> list[dict]:
        """List validated interfaces in the catalog."""
        return service.list()

    @server.tool()
    def search_interfaces(query: str) -> list[dict]:
        """Search validated interfaces by ID, system, protocol, owner or business object."""
        return service.search(query)

    @server.tool()
    def get_interface(interface_id: str) -> dict:
        """Get one validated interface summary with source revision context."""
        item=service.get(interface_id)
        return item or {"error":"not_found","interface_id":interface_id}

    @server.tool()
    def get_interface_operations(interface_id: str) -> dict:
        """Return readiness summary, ownership and source path for support/architecture context."""
        item=service.get(interface_id)
        if not item:return {"error":"not_found","interface_id":interface_id}
        return {"id":item["id"],"owner":item.get("owner"),"findings":item.get("findings",{}),"source_path":item.get("path"),"catalog":str(service.path)}

    return server


def main() -> None:
    p=argparse.ArgumentParser(prog="interface-as-code-mcp")
    p.add_argument("--catalog",default=os.getenv("INTERFACE_AS_CODE_CATALOG","generated/catalog/index.json"))
    args=p.parse_args()
    create_server(args.catalog).run()

if __name__=="__main__":main()
