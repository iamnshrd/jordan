#!/usr/bin/env python3
from __future__ import annotations

import json


def simulate_dispatch(users: list[dict], decisions: dict[str, dict]) -> list[dict]:
    outputs = []
    for item in users:
        if not item.get('enabled', True):
            continue
        user_id = item.get('user_id', '')
        target = item.get('target', '')
        if user_id == 'default':
            outputs.append({'user_id': user_id, 'skip': True, 'skip_reason': 'default-user-id-blocked'})
            continue
        if not target:
            outputs.append({'user_id': user_id, 'skip': True, 'skip_reason': 'missing-user-target'})
            continue
        decision = decisions.get(user_id, {'skip': True, 'skip_reason': 'no-decision', 'should_send': False, 'delivered': False})
        outputs.append({'user_id': user_id, 'target': target, **decision})
    return outputs


def main() -> None:
    users = [
        {'user_id': 'telegram:10001', 'target': '10001', 'enabled': True},
        {'user_id': 'telegram:10002', 'target': '10002', 'enabled': True},
        {'user_id': 'telegram:10003', 'target': '10003', 'enabled': True},
        {'user_id': 'telegram:10004', 'target': '10004', 'enabled': True},
        {'user_id': 'telegram:10005', 'target': '10005', 'enabled': True},
    ]
    decisions = {
        'telegram:10001': {'skip': False, 'skip_reason': '', 'should_send': True, 'delivered': True, 'event_type': 'open-loop-followup'},
        'telegram:10002': {'skip': True, 'skip_reason': 'cooldown-active', 'should_send': False, 'delivered': False, 'event_type': None},
        'telegram:10003': {'skip': False, 'skip_reason': '', 'should_send': True, 'delivered': True, 'event_type': 'commitment-check'},
        'telegram:10004': {'skip': True, 'skip_reason': 'awaiting-user-reengagement', 'should_send': False, 'delivered': False, 'event_type': None},
        'telegram:10005': {'skip': False, 'skip_reason': '', 'should_send': True, 'delivered': True, 'event_type': 'broken-promise-check'},
    }
    outputs = simulate_dispatch(users, decisions)
    senders = [x for x in outputs if x.get('should_send')]
    skippers = [x for x in outputs if x.get('skip')]
    results = [
        {
            'name': 'five_users_produce_five_separate_outputs',
            'pass': len(outputs) == 5 and len({x['user_id'] for x in outputs}) == 5,
        },
        {
            'name': 'mixed_send_and_skip_distribution',
            'pass': len(senders) == 3 and len(skippers) == 2,
        },
        {
            'name': 'per_user_targets_preserved',
            'pass': all(x.get('target') == x.get('user_id').split(':', 1)[1] for x in outputs if x.get('user_id', '').startswith('telegram:')),
        },
        {
            'name': 'distinct_skip_reasons_preserved',
            'pass': {'cooldown-active', 'awaiting-user-reengagement'}.issubset({x.get('skip_reason') for x in outputs}),
        },
    ]
    total = len(results)
    passed = sum(1 for x in results if x.get('pass'))
    print(json.dumps({'total': total, 'pass': passed, 'results': results, 'outputs': outputs}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if total == passed else 1)


if __name__ == '__main__':
    main()
