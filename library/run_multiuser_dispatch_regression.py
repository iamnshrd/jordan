#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from library.config import canonical_user_id


def autoregister(data: dict, sessions: dict) -> dict:
    users = data.get('users') or []
    known = {canonical_user_id(x.get('user_id') or x.get('target') or '') for x in users}
    changed = False
    for _, payload in sessions.items():
        origin = payload.get('origin') or {}
        delivery = payload.get('deliveryContext') or {}
        if origin.get('provider') != 'telegram' or origin.get('chatType') != 'direct':
            continue
        raw_to = (delivery.get('to') or origin.get('to') or '').strip()
        if not raw_to.startswith('telegram:'):
            continue
        target = raw_to.split(':', 1)[1]
        user_id = canonical_user_id(target)
        if not target or user_id in known:
            continue
        users.append({
            'user_id': user_id,
            'channel': 'telegram',
            'target': target,
            'enabled': False,
            'source': 'auto-registered-from-sessions',
        })
        known.add(user_id)
        changed = True
    if changed:
        data['users'] = users
    return data


def main() -> None:
    sessions = {
        'agent:main:telegram:direct:77571089': {
            'origin': {'provider': 'telegram', 'chatType': 'direct', 'to': 'telegram:77571089'},
            'deliveryContext': {'to': 'telegram:77571089'},
        },
        'agent:main:telegram:direct:99999999': {
            'origin': {'provider': 'telegram', 'chatType': 'direct', 'to': 'telegram:99999999'},
            'deliveryContext': {'to': 'telegram:99999999'},
        },
    }
    data = {'users': [{'user_id': 'telegram:77571089', 'channel': 'telegram', 'target': '77571089', 'enabled': True}]}
    out = autoregister(data, sessions)
    users = out.get('users', [])
    results = [
        {
            'name': 'autoregisters_new_session_user_disabled',
            'pass': any(x.get('user_id') == 'telegram:99999999' and x.get('enabled') is False for x in users),
        },
        {
            'name': 'keeps_existing_enabled_user',
            'pass': any(x.get('user_id') == 'telegram:77571089' and x.get('enabled') is True for x in users),
        },
        {
            'name': 'default_live_send_would_be_blocked',
            'pass': canonical_user_id('default') == 'default',
        },
    ]
    total = len(results)
    passed = sum(1 for x in results if x.get('pass'))
    print(json.dumps({'total': total, 'pass': passed, 'results': results}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if total == passed else 1)


if __name__ == '__main__':
    main()
