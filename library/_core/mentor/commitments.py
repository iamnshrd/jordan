"""Commitment extraction and follow-up helpers for the mentor layer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from library.config import get_default_store
from library._core.state_store import StateStore, KEY_COMMITMENTS
from library._core.runtime.routes import infer_route
from library.utils import now_iso

ACTION_MARKERS = [
    'сделаю', 'сделать', 'начну', 'начать', 'напишу', 'позвоню', 'поговорю',
    'пойду', 'попробую', 'соберу', 'разберу', 'запишу', 'отправлю', 'решу',
]

RESOLUTION_MARKERS = [
    'сделал', 'сделала', 'сделано', 'получилось', 'написал', 'написала',
    'поговорил', 'поговорила', 'позвонил', 'позвонила', 'отправил', 'отправила',
    'закончил', 'закончила', 'закрыл', 'закрыла', 'разобрал', 'разобрала',
]

TIME_CUES = {
    'сегодня': 0,
    'сегодня вечером': 0,
    'сегодня ночью': 0,
    'завтра': 1,
    'послезавтра': 2,
}

STRONG_COMMITMENT_MARKERS = [
    'точно', 'обязательно', 'сделаю', 'напишу', 'поговорю', 'завтра', 'сегодня', 'до вечера'
]

SOFT_COMMITMENT_MARKERS = [
    'может', 'постараюсь', 'попробую', 'наверное', 'если получится'
]


def load_commitments(user_id: str = 'default', store: StateStore | None = None) -> dict:
    store = store or get_default_store()
    data = store.get_json(user_id, KEY_COMMITMENTS, default={}) or {}
    data.setdefault('items', [])
    return data


def save_commitments(data: dict, user_id: str = 'default', store: StateStore | None = None) -> dict:
    store = store or get_default_store()
    store.put_json(user_id, KEY_COMMITMENTS, data)
    return data


def _is_overdue(due_at: str) -> bool:
    try:
        due = datetime.fromisoformat((due_at or '').replace('Z', '+00:00'))
        return due < datetime.now(timezone.utc)
    except Exception:
        return False


def _commitment_strength(summary: str) -> str:
    s = summary.lower()
    strong_hits = sum(1 for x in STRONG_COMMITMENT_MARKERS if x in s)
    soft_hits = sum(1 for x in SOFT_COMMITMENT_MARKERS if x in s)
    if strong_hits >= 2 and soft_hits == 0:
        return 'hard'
    if soft_hits >= 1:
        return 'soft'
    return 'standard'


def _parse_due_hint(summary: str) -> dict:
    s = summary.lower()
    now = datetime.now(timezone.utc)
    for cue, delta_days in TIME_CUES.items():
        if cue in s:
            due = (now + timedelta(days=delta_days)).replace(hour=20, minute=0, second=0, microsecond=0)
            return {'cue': cue, 'due_at': due.isoformat()}
    if 'до вечера' in s:
        due = now.replace(hour=20, minute=0, second=0, microsecond=0)
        return {'cue': 'до вечера', 'due_at': due.isoformat()}
    if 'на этой неделе' in s:
        due = (now + timedelta(days=max(1, 6 - now.weekday()))).replace(hour=20, minute=0, second=0, microsecond=0)
        return {'cue': 'на этой неделе', 'due_at': due.isoformat()}
    return {'cue': '', 'due_at': ''}


def _action_core(summary: str) -> str:
    s = summary.strip()
    lowered = s.lower()
    prefixes = ['завтра ', 'сегодня ', 'послезавтра ', 'до вечера ', 'на этой неделе ']
    for prefix in prefixes:
        if lowered.startswith(prefix):
            s = s[len(prefix):]
            lowered = s.lower()
            break
    return _normalize_summary(s)


def _normalize_summary(text: str) -> str:
    s = ' '.join((text or '').strip().split())
    s = s.strip(' .,!?:;')
    return s[:240]


def infer_commitment(question: str) -> str:
    q = _normalize_summary(question)
    q_lower = q.lower()
    if not q:
        return ''
    if not any(marker in q_lower for marker in ACTION_MARKERS):
        return ''

    prefixes = ['я ', 'ну ', 'ладно, ', 'ок, ', 'хорошо, ', 'тогда ']
    lowered = q.lower()
    for prefix in prefixes:
        if lowered.startswith(prefix):
            q = q[len(prefix):]
            lowered = q.lower()

    splitters = [' но ', ' потому что ', ' если ', ' хотя ', ' просто ']
    for splitter in splitters:
        idx = lowered.find(splitter)
        if idx > 0:
            q = q[:idx]
            lowered = q.lower()
            break

    return _normalize_summary(q)


def record_commitment(question: str, route: str = '', user_id: str = 'default', store: StateStore | None = None) -> dict | None:
    summary = infer_commitment(question)
    if not summary:
        return None
    data = load_commitments(user_id=user_id, store=store)
    items = data.get('items', [])
    for item in items:
        if item.get('summary') == summary and item.get('status') == 'open':
            item['count'] = int(item.get('count', 1) or 1) + 1
            item['last_seen'] = now_iso()
            if route:
                item['route'] = route
            save_commitments(data, user_id=user_id, store=store)
            return item
    inferred_route = route or infer_route(summary)
    summary_lower = summary.lower()
    if inferred_route == 'general' and any(x in summary_lower for x in ['ему', 'ей', 'с ним', 'с ней', 'разговор', 'напис', 'поговор']):
        inferred_route = 'relationship-maintenance'
    due = _parse_due_hint(summary)
    item = {
        'summary': summary,
        'action_core': _action_core(summary),
        'route': inferred_route,
        'status': 'open',
        'count': 1,
        'strength': _commitment_strength(summary),
        'created_at': now_iso(),
        'last_seen': now_iso(),
        'last_prompted_at': '',
        'due_hint': due.get('cue', ''),
        'due_at': due.get('due_at', ''),
    }
    items.insert(0, item)
    data['items'] = items[:20]
    save_commitments(data, user_id=user_id, store=store)
    return item


def best_open_commitment(route: str = '', user_id: str = 'default', store: StateStore | None = None) -> dict | None:
    data = load_commitments(user_id=user_id, store=store)
    candidates = [x for x in (data.get('items') or []) if x.get('status') == 'open']
    if not candidates:
        return None
    now = datetime.now(timezone.utc)

    def score(item: dict) -> tuple[int, int]:
        s = 50 + int(item.get('count', 1) or 1)
        strength = item.get('strength', 'standard')
        if strength == 'hard':
            s += 18
        elif strength == 'soft':
            s -= 8
        if route and item.get('route') == route:
            s += 20
        if item.get('last_prompted_at'):
            s -= 15
        due_at = item.get('due_at') or ''
        if due_at:
            try:
                due = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                delta = (due - now).total_seconds()
                if delta <= 0:
                    s += 45
                elif delta <= 6 * 3600:
                    s += 35
                elif delta <= 48 * 3600:
                    s += 25
                elif delta <= 7 * 24 * 3600:
                    s += 5
                else:
                    s -= 10
            except Exception:
                pass
        return (s, int(item.get('count', 1) or 1))
    ranked = sorted(candidates, key=score, reverse=True)
    return ranked[0]


def commitment_prompt_style(item: dict) -> str:
    strength = item.get('strength', 'standard')
    if strength == 'hard':
        return 'hard'
    if strength == 'soft':
        return 'gentle'
    return 'standard'


def commitment_summary(user_id: str = 'default', store: StateStore | None = None) -> dict:
    data = load_commitments(user_id=user_id, store=store)
    items = data.get('items', [])
    open_items = [x for x in items if x.get('status') == 'open']
    resolved_items = [x for x in items if x.get('status') == 'resolved']
    return {
        'open_total': len(open_items),
        'resolved_total': len(resolved_items),
        'hard_open': len([x for x in open_items if x.get('strength') == 'hard']),
        'soft_open': len([x for x in open_items if x.get('strength') == 'soft']),
        'top_open': [
            {
                'summary': x.get('summary', ''),
                'strength': x.get('strength', 'standard'),
                'due_hint': x.get('due_hint', ''),
                'route': x.get('route', ''),
            }
            for x in open_items[:5]
        ],
        'top_resolved': [
            {
                'summary': x.get('summary', ''),
                'strength': x.get('strength', 'standard'),
                'route': x.get('route', ''),
            }
            for x in resolved_items[:3]
        ],
        'overdue_hard': len([x for x in open_items if x.get('strength') == 'hard' and x.get('due_at') and _is_overdue(x.get('due_at'))]),
        'repeated_hard': len([x for x in open_items if x.get('strength') == 'hard' and int(x.get('count', 1) or 1) >= 2]),
        'vague_soft': len([x for x in open_items if x.get('strength') == 'soft' and x.get('route') in {'general', 'career-vocation'}]),
        'movement_signal': 'moving' if resolved_items else ('stuck' if open_items else 'clear'),
        'next_focus': (open_items[0].get('summary', '') if open_items else ''),
    }


def mark_commitment_prompted(summary: str, user_id: str = 'default', store: StateStore | None = None) -> None:
    data = load_commitments(user_id=user_id, store=store)
    for item in data.get('items', []):
        if item.get('summary') == summary and item.get('status') == 'open':
            item['last_prompted_at'] = now_iso()
            break
    save_commitments(data, user_id=user_id, store=store)


def maybe_resolve_from_reply(question: str, user_id: str = 'default', store: StateStore | None = None) -> dict | None:
    q = (question or '').lower()
    if not any(marker in q for marker in RESOLUTION_MARKERS):
        return None
    data = load_commitments(user_id=user_id, store=store)
    items = [x for x in data.get('items', []) if x.get('status') == 'open']
    if not items:
        return None
    question_route = infer_route(question)
    if question_route == 'general' and any(x in q for x in ['ему', 'ей', 'с ним', 'с ней', 'разговор', 'написал', 'написала', 'поговорил', 'поговорила']):
        question_route = 'relationship-maintenance'
    ranked: list[tuple[int, dict]] = []
    for item in items:
        route = item.get('route', '')
        summary = (item.get('summary') or '').lower()
        action_core = (item.get('action_core') or '').lower()
        score = 0
        if route and route == question_route:
            score += 15
        stop = {'этот', 'это', 'того', 'вот', 'ему', 'ей'}
        for word in summary.split():
            if len(word) >= 4 and word not in stop and word in q:
                score += 3
        for word in action_core.split():
            if len(word) >= 4 and word not in stop and word in q:
                score += 4
        ranked.append((score, item))
    ranked.sort(key=lambda x: x[0], reverse=True)
    if ranked and ranked[0][0] >= 4:
        item = ranked[0][1]
        item['status'] = 'resolved'
        item['resolved_at'] = now_iso()
        save_commitments(data, user_id=user_id, store=store)
        return item
    return None


def resolve_commitment(summary: str, user_id: str = 'default', store: StateStore | None = None) -> None:
    data = load_commitments(user_id=user_id, store=store)
    for item in data.get('items', []):
        if item.get('summary') == summary and item.get('status') == 'open':
            item['status'] = 'resolved'
            item['resolved_at'] = now_iso()
            break
    save_commitments(data, user_id=user_id, store=store)
