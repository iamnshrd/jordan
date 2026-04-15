#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from library._core.mentor.tick import tick
from library.config import (
    load_tracked_mentor_users,
    save_tracked_mentor_users,
    canonical_user_id,
)
from library.mentor_targets_admin import normalize_targets


SESSIONS_PATH = Path('/root/.openclaw-jordan-peterson/agents/main/sessions/sessions.json')
LEGACY_TARGET = canonical_user_id('77571089')


def _bootstrap_legacy_user() -> dict:
    data = load_tracked_mentor_users()
    users = data.get('users') or []
    if users:
        return normalize_targets()
    data = {
        'users': [
            {
                'user_id': LEGACY_TARGET,
                'channel': 'telegram',
                'target': '77571089',
                'enabled': True,
                'auto_onboard': 'manual-review',
            }
        ]
    }
    save_tracked_mentor_users(data)
    return normalize_targets()


def _read_sessions() -> dict:
    if not SESSIONS_PATH.exists():
        return {}
    try:
        data = json.loads(SESSIONS_PATH.read_text(encoding='utf-8'))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _autoregister_from_sessions(data: dict) -> dict:
    sessions = _read_sessions()
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
            'auto_onboard': 'manual-review',
            'source': 'auto-registered-from-sessions',
        })
        known.add(user_id)
        changed = True
    if changed:
        data['users'] = users
        save_tracked_mentor_users(data)
    return normalize_targets()


def main() -> None:
    data = _bootstrap_legacy_user()
    data = _autoregister_from_sessions(data)
    outputs = []
    for item in data.get('users', []):
        if not item.get('enabled', True):
            continue
        user_id = canonical_user_id(item.get('user_id') or item.get('target') or 'default')
        channel = (item.get('channel') or 'telegram').strip() or 'telegram'
        target = (item.get('target') or '').strip()
        if user_id == 'default':
            outputs.append({
                'user_id': user_id,
                'channel': channel,
                'target': target,
                'skip': True,
                'skip_reason': 'default-user-id-blocked',
                'should_send': False,
                'sent': False,
                'delivered': False,
            })
            continue
        if not target:
            outputs.append({
                'user_id': user_id,
                'channel': channel,
                'target': target,
                'skip': True,
                'skip_reason': 'missing-user-target',
                'should_send': False,
                'sent': False,
                'delivered': False,
            })
            continue

        result = tick(send=True, user_id=user_id)
        event = result.get('selected_event') or {}
        compact = {
            'user_id': user_id,
            'channel': channel,
            'target': target,
            'route': result.get('route'),
            'skip': result.get('skip'),
            'skip_reason': result.get('skip_reason'),
            'event_type': event.get('type'),
            'event_summary': event.get('summary'),
            'should_send': result.get('should_send'),
            'sent': result.get('sent'),
        }

        msg = (result.get('rendered_message') or '').strip()
        if result.get('should_send') and msg:
            subprocess.run([
                'openclaw', '--profile', 'jordan-peterson', 'message', 'send',
                '--channel', channel,
                '--target', target,
                '--message', msg,
            ], check=True)
            compact['delivered'] = True
        else:
            compact['delivered'] = False
        outputs.append(compact)

    print(json.dumps(outputs, ensure_ascii=False))


if __name__ == '__main__':
    main()
