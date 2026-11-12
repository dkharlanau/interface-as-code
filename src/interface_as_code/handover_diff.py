"""Compare two declared handovers, without transferring approval or running checks."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .diffing import semantic_diff
from .handover import _build_handover, _load_contract, _text, render_handover
from .loader import SpecLoadError


def build_handover_diff(previous: str | Path, current: str | Path) -> dict[str, Any]:
    old_source, old_bytes, old = _load_contract(previous)
    new_source, new_bytes, new = _load_contract(current)
    if old['interface']['id'] != new['interface']['id']:
        raise SpecLoadError('Handover comparison requires the same interface.id; review identity changes separately.')
    before = _build_handover(old_source, old_bytes, old)
    after = _build_handover(new_source, new_bytes, new)
    changes = [change.to_dict() for change in semantic_diff(old, new)]
    review = []
    if changes:
        review = [
            {'area': 'contacts', 'paths': ['$.monitoring.owner', '$.ownership', '$.monitoring.support_route'],
             'question': 'Do the declared teams accept support for the changed declaration and its source/target?',
             'previous': before['declared_contacts'], 'current': after['declared_contacts']},
            {'area': 'recovery', 'paths': ['$.delivery', '$.retry'],
             'question': 'Do the declared delivery and replay preconditions still apply, and who authorizes recovery?',
             'previous': before['declared_controls']['recovery'], 'current': after['declared_controls']['recovery']},
            {'area': 'reconciliation', 'paths': ['$.reconciliation'],
             'question': 'Will this comparison and business key establish the intended state in the changed target?',
             'previous': before['declared_controls']['reconciliation'], 'current': after['declared_controls']['reconciliation']},
            {'area': 'test_intent', 'paths': ['$.tests', '$.evidence'],
             'question': 'Which proposed checks need execution and evidence against this exact declaration?',
             'previous': before['proposed_test_plan'], 'current': after['proposed_test_plan']},
        ]
    return {
        'format': 'interface-as-code-handover-diff/1.0',
        'interface_id': new['interface']['id'],
        'previous_source': before['source'], 'current_source': after['source'],
        'source_bytes_changed': old_bytes != new_bytes,
        'change_counts': {level: sum(c['severity'] == level for c in changes)
                          for level in ('breaking', 'high-risk', 'review', 'informational')},
        'changes': changes,
        'review_scope': review,
        'review_scope_basis': 'Any semantic change opens four general handover review areas; this is not dependency or runtime impact analysis.',
        'reference_content_comparison': 'not_performed',
        'acceptance': {'status': 'not_assessed', 'previous_approval_transferred': False,
                       'replay_authority': 'not_granted', 'test_execution': 'not_performed',
                       'evidence_verification': 'not_performed'},
        'previous_handover': before, 'current_handover': after,
        'limits': [
            'Existing semantic_diff classifications are reused without changing their severity rules.',
            'The source hashes bind YAML bytes only. An unchanged reference can point to changed contents that this report did not compare.',
            'Identical proposed tests or evidence links are not evidence of acceptance for the changed target or mapping.',
            'Review scope is a conservative checklist, not proof that a particular control failed or a test must be rerun.',
            'No observed data is compared; evidence is neither fetched nor invalidated in an external registry.',
            'An empty semantic diff or exit 0 does not approve either declaration.',
        ],
    }


def handover_diff_gate(report: dict[str, Any], change_threshold: str, readiness_threshold: str) -> dict[str, Any]:
    change_ranks = {'breaking': 4, 'high-risk': 3, 'review': 2, 'informational': 1, 'none': 99}
    readiness_ranks = {'error': 3, 'warning': 2, 'info': 1, 'none': 99}
    change_blocks = sum(change_ranks[c['severity']] >= change_ranks[change_threshold] for c in report['changes'])
    readiness_blocks = sum(readiness_ranks[q['severity']] >= readiness_ranks[readiness_threshold]
                           for q in report['current_handover']['readiness']['questions'])
    return {'change_threshold': change_threshold, 'current_readiness_threshold': readiness_threshold,
            'change_findings_at_threshold': change_blocks, 'readiness_findings_at_threshold': readiness_blocks,
            'exit': 1 if change_blocks or readiness_blocks else 0,
            'meaning': 'Declared change/readiness gate only; not acceptance or replay permission.'}


def render_handover_diff(report: dict[str, Any]) -> str:
    lines = ['# Support handover change review', '', f"Interface: {_text(report['interface_id'])}",
             '**Previous approval is not transferred. Neither declaration is accepted by this report.**', '',
             f"Previous: {_text(report['previous_source']['path'])}",
             f"Previous SHA-256: {report['previous_source']['sha256']}",
             f"Current: {_text(report['current_source']['path'])}",
             f"Current SHA-256: {report['current_source']['sha256']}", '',
             '## Changed declarations', '']
    if not report['changes']:
        lines.append('No semantic changes found by the existing diff rules. Referenced contents were not compared.')
    for c in report['changes']:
        lines += [f"- {c['severity'].upper()} {_text(c['path'])}: {_text(c['old'])} → {_text(c['new'])}. {c['reason']}"]
    if 'gate' in report:
        g = report['gate']
        lines += ['', '## Requested gate', '',
                  f"Change threshold: {g['change_threshold']}; findings: {g['change_findings_at_threshold']}.",
                  f"Current readiness threshold: {g['current_readiness_threshold']}; findings: {g['readiness_findings_at_threshold']}.",
                  f"Exit: {g['exit']}. {g['meaning']}"]
    lines += ['', '## What needs human review', '', report['review_scope_basis'], '']
    for item in report['review_scope']:
        lines += [f"### {item['area'].replace('_', ' ').title()}",
                  'Contract paths: ' + ', '.join(item['paths']), item['question'],
                  'Values below are declarations; unchanged text is not renewed acceptance.']
        if item['area'] == 'contacts':
            old_contacts = {c['role']: c for c in item['previous']}
            for c in item['current']:
                lines.append(f"- {c['role']} ({c['path']}): {_text(old_contacts[c['role']]['declared_value'])} → {_text(c['declared_value'])}.")
        elif item['area'] == 'test_intent':
            old_cases = {c['id']: c for c in item['previous']['cases']}
            new_cases = {c['id']: c for c in item['current']['cases']}
            for case_id in sorted(set(old_cases) | set(new_cases)):
                old_case, new_case = old_cases.get(case_id), new_cases.get(case_id)
                if old_case == new_case:
                    lines.append(f"- {_text(case_id)}: unchanged proposed check; applicability and execution still need review.")
                else:
                    lines.append(f"- {_text(case_id)}: {_text(old_case)} → {_text(new_case)}. Not executed.")
        else:
            for field in sorted(set(item['previous']) | set(item['current'])):
                lines.append(f"- {field}: {_text(item['previous'].get(field))} → {_text(item['current'].get(field))}.")
        lines.append('')
    lines += ['## Limits', '', *[f'- {x}' for x in report['limits']], '',
              '---', '', 'Current declaration brief follows. Proposed checks have not run.', '',
              render_handover(report['current_handover'])]
    return '\n'.join(lines)
