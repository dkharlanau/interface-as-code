"""Exercise the synthetic support-handover query over an actual MCP stdio session."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


async def check(catalog: Path) -> dict:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=['-m', 'interface_as_code.mcp_server', '--catalog', str(catalog.resolve())],
    )
    async with stdio_client(parameters) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            tools = {tool.name for tool in (await session.list_tools()).tools}
            require(tools == {'list_interfaces', 'search_interfaces', 'get_interface',
                             'get_interface_operations', 'get_interface_handover', 'get_catalog_status'},
                    'Unexpected server tool surface')
            reply = await session.call_tool('get_interface_handover',
                                           {'interface_id': 'SYNTHETIC-CUSTOMER-HANDOVER-GAPS'})
            require(not reply.is_error, 'Handover tool failed')
            answer = reply.structured_content
            if answer is None:
                require(len(reply.content) == 1 and reply.content[0].type == 'text',
                        'Expected one JSON text result')
                answer = json.loads(reply.content[0].text)
            require(isinstance(answer, dict), 'Expected handover object')
            brief = answer['handover']
            require(brief['readiness']['counts'] == {'error': 2, 'warning': 3, 'info': 1},
                    'Synthetic readiness result changed')
            require(brief['acceptance'] == {'status': 'not_assessed', 'replay_authority': 'not_granted',
                                           'test_execution': 'not_performed', 'evidence_verification': 'not_performed'},
                    'Response must not grant acceptance or execution authority')
            unknown = await session.call_tool('get_interface_handover', {'interface_id': '../../outside-catalog'})
            require(not unknown.is_error, 'Unknown-ID tool call failed')
            unknown_data = unknown.structured_content
            if unknown_data is None:
                require(len(unknown.content) == 1 and unknown.content[0].type == 'text',
                        'Expected one unknown-ID JSON text result')
                unknown_data = json.loads(unknown.content[0].text)
            require(isinstance(unknown_data, dict) and unknown_data.get('error') == 'not_found',
                    'Unknown ID must not be a filesystem request')
            return {'transport': 'MCP stdio', 'tools': sorted(tools),
                    'interface_id': answer['interface_id'], 'readiness_counts': brief['readiness']['counts'],
                    'source_sha256': brief['source']['sha256'], 'catalog_snapshot': answer['catalog_snapshot'],
                    'acceptance': brief['acceptance'], 'unknown_id': 'not_found',
                    'runtime_or_llm_execution': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(check(args.catalog)), indent=2))
