#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from library.config import (
    load_tracked_mentor_users,
    save_tracked_mentor_users,
    canonical_user_id,
    WORKSPACE,
)


AUTO_ENABLE_GRACE_COUNT = 0


def list_targets() -> dict:
    data = load_tracked_mentor_users()
    data.setdefault('users', [])
    return data


def _target_dir(user_id: str) -> Path:
    uid = canonical_user_id(user_id)
    if uid == 'default':
        return WORKSPACE
    return WORKSPACE / uid


def _target_has_meaningful_state(user_id: str) -> bool:
    d = _target_dir(user_id)
    if not d.exists() or not d.is_dir():
        return False
    interesting = [
        'mentor_state.json',
        'mentor_events.jsonl',
        'continuity.json',
        'session_state.json',
        'commitments.json',
    ]
    return any((d / name).exists() for name in interesting)


def _auto_policy(item: dict) -> dict:
    out = dict(item)
    out.setdefault('enabled', False)
    out.setdefault('auto_onboard', 'manual-review')
    out['has_state'] = _target_has_meaningful_state(out.get('user_id') or out.get('target') or '')
    return out


def normalize_targets() -> dict:
    data = load_tracked_mentor_users()
    users = []
    seen = set()
    for item in data.get('users', []):
        uid = canonical_user_id(item.get('user_id') or item.get('target') or '')
        if not uid or uid in seen:
            continue
        seen.add(uid)
        merged = dict(item)
        merged['user_id'] = uid
        if not merged.get('target') and ':' in uid:
            merged['target'] = uid.split(':', 1)[1]
        users.append(_auto_policy(merged))
    data['users'] = users
    save_tracked_mentor_users(data)
    return data


def upsert_target(user_id: str, *, channel: str = 'telegram', target: str = '', enabled: bool | None = None, auto_onboard: str | None = None) -> dict:
    data = normalize_targets()
    users = data.get('users') or []
    uid = canonical_user_id(user_id or target)
    found = None
    for item in users:
        if canonical_user_id(item.get('user_id') or item.get('target') or '') == uid:
            found = item
            break
    if found is None:
        found = {
            'user_id': uid,
            'channel': channel,
            'target': target or (uid.split(':', 1)[1] if ':' in uid else uid),
            'enabled': bool(enabled) if enabled is not None else False,
            'auto_onboard': auto_onboard or 'manual-review',
        }
        users.append(found)
    else:
        if channel:
            found['channel'] = channel
        if target:
            found['target'] = target
        if enabled is not None:
            found['enabled'] = bool(enabled)
        if auto_onboard:
            found['auto_onboard'] = auto_onboard
    data['users'] = [_auto_policy(x) for x in users]
    save_tracked_mentor_users(data)
    return data


def set_enabled(user_id: str, enabled: bool) -> dict:
    uid = canonical_user_id(user_id)
    return upsert_target(uid, enabled=enabled)


def remove_target(user_id: str) -> dict:
    uid = canonical_user_id(user_id)
    data = normalize_targets()
    data['users'] = [
        item for item in (data.get('users') or [])
        if canonical_user_id(item.get('user_id') or item.get('target') or '') != uid
    ]
    save_tracked_mentor_users(data)
    return data


def onboarding_report() -> dict:
    data = normalize_targets()
    users = data.get('users') or []
    return {
        'total_users': len(users),
        'enabled_users': len([x for x in users if x.get('enabled')]),
        'manual_review_users': [x for x in users if x.get('auto_onboard') == 'manual-review' and not x.get('enabled')],
        'users_with_state': [x for x in users if x.get('has_state')],
    }


def legacy_default_report() -> dict:
    root = WORKSPACE
    legacy_files = []
    for name in [
        'mentor_state.json', 'mentor_events.jsonl', 'mentor_delays.json',
        'continuity.json', 'continuity_summary.json', 'session_state.json',
        'user_state.json', 'effectiveness_memory.json', 'progress_state.json',
        'context_graph.json', 'user_reaction_estimate.json', 'commitments.json',
        'session_checkpoints.jsonl',
    ]:
        p = root / name
        if p.exists():
            legacy_files.append(name)
    return {
        'legacy_default_files': legacy_files,
        'count': len(legacy_files),
    }
