"""Rehearse read-only agent context on a synthetic MDG-to-S/4 support gap."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from interface_as_code.catalog_service import CatalogService


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run(output: Path) -> dict:
    root = Path(__file__).resolve().parents[1]
    source = root / 'examples/governance/handover-gaps.yaml'
    # Never overwrite an earlier rehearsal or silently replace its evidence.
    output.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, '-m', 'interface_as_code.cli', 'catalog', str(source),
               '-o', str(output/'catalog'), '--include-handover']
    result = subprocess.run(command, cwd=root, capture_output=True, text=True)
    require(result.returncode == 0, f'Catalog generation failed: {result.stderr}')
    service = CatalogService(output/'catalog')
    interface_id = 'SYNTHETIC-CUSTOMER-HANDOVER-GAPS'
    answer = service.handover(interface_id)
    brief = answer['handover']
    questions = brief['readiness']['questions']
    require(brief['source']['sha256'] == hashlib.sha256(source.read_bytes()).hexdigest(),
            'Source bytes do not match the retained handover')
    require(brief['readiness']['counts'] == {'error': 2, 'warning': 3, 'info': 1},
            'Expected synthetic support gaps changed')
    codes = {q['code'] for q in questions}
    require({'owner.missing','support.route-missing','recoverability.replay-guidance-missing',
             'reconciliation.comparison-missing'} <= codes, 'Missing an expected support question')
    require(brief['acceptance']['status'] == 'not_assessed' and
            brief['acceptance']['replay_authority'] == 'not_granted', 'Unexpected approval or replay authority')
    require(all('handover' not in item for item in service.list()), 'List expands every handover')
    require(service.handover('../../outside-catalog')['error'] == 'not_found',
            'Unknown ID must not become a filesystem request')
    receipt = {
        'scenario': 'Synthetic customer approval has an unresolved support handover before replication into SAP S/4HANA.',
        'architecture': 'Validate once; retain questions in a catalog snapshot; query by exact interface ID. No ERP or LLM execution.',
        'catalog_cli_exit': result.returncode,
        'interface_id': interface_id,
        'readiness_counts': brief['readiness']['counts'],
        'questions': questions,
        'acceptance': brief['acceptance'],
        'source': answer['provenance'],
        'catalog_snapshot': answer['catalog_snapshot'],
        'unknown_id': 'not_found',
        'mcp_transport_exercised': False,
        'business_result_measured': False,
        'limits': ['Synthetic declaration, not customer or SAP runtime evidence.',
                   'Structural validity and a generated catalog do not establish operational readiness.',
                   'Catalog hash binds loaded bytes, not authenticity or freshness.',
                   'This rehearsal uses the same CatalogService as MCP, not a model or MCP client.'],
    }
    (output/'result.json').write_text(json.dumps(receipt, indent=2)+'\n',encoding='utf-8')
    return receipt


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        result=run(args.output)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1,f'{exc}\n')
    print(json.dumps(result,indent=2))
