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
        decision = decisions.get(user_id, {'skip': True, 'skip_reason': 'no-decision'})
        outputs.append({'user_id': user_id, **decision})
    return outputs


def main() -> None:
    users = [
        {'user_id': 'telegram:111', 'target': '111', 'enabled': True},
        {'user_id': 'telegram:222', 'target': '222', 'enabled': True},
    ]
    decisions = {
        'telegram:111': {'skip': False, 'skip_reason': '', 'should_send': True, 'delivered': True},
        'telegram:222': {'skip': True, 'skip_reason': 'cooldown-active', 'should_send': False, 'delivered': False},
    }
    outputs = simulate_dispatch(users, decisions)
    by_user = {x['user_id']: x for x in outputs}
    results = [
        {
            'name': 'user_a_can_send_while_user_b_skips',
            'pass': by_user['telegram:111'].get('should_send') is True and by_user['telegram:222'].get('skip_reason') == 'cooldown-active',
        },
        {
            'name': 'per_user_outputs_stay_separate',
            'pass': len(outputs) == 2 and outputs[0]['user_id'] != outputs[1]['user_id'],
        },
        {
            'name': 'default_user_would_be_blocked',
            'pass': simulate_dispatch([{'user_id': 'default', 'target': '333', 'enabled': True}], {})[0]['skip_reason'] == 'default-user-id-blocked',
        },
    ]
    total = len(results)
    passed = sum(1 for x in results if x.get('pass'))
    print(json.dumps({'total': total, 'pass': passed, 'results': results}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if total == passed else 1)


if __name__ == '__main__':
    main()
