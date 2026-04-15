"""Mentor effectiveness summaries and self-audit helpers."""

from __future__ import annotations

from library.config import canonical_user_id, get_default_store
from library._core.state_store import StateStore, KEY_MENTOR_STATE, KEY_MENTOR_DELAYS


def summarize(user_id: str = 'default', store: StateStore | None = None) -> dict:
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    state = store.get_json(user_id, KEY_MENTOR_STATE, default={}) or {}
    outcomes = state.get('event_outcomes') or {}
    rows = []
    route_rows: dict[str, dict] = {}
    total_followthrough = 0
    total_theater = 0
    total_truthful_delay = 0
    total_lazy_delay = 0

    delay_memory = store.get_json(user_id, KEY_MENTOR_DELAYS, default={'items': []}) or {'items': []}
    delay_items = list(delay_memory.get('items') or [])
    pending_delays = [x for x in delay_items if x.get('status') == 'pending']
    resolved_helpful_delays = [x for x in delay_items if x.get('status') == 'resolved-helpful']
    delay_by_event: dict[str, dict] = {}
    delay_by_route: dict[str, dict] = {}
    for item in delay_items:
        route = item.get('route', '')
        event_type = item.get('event_type', '')
        status = item.get('status', '')
        key = f'{route}::{event_type}' if route and event_type else ''
        if key:
            agg = delay_by_event.setdefault(key, {'pending': 0, 'resolved_helpful': 0})
            if status == 'pending':
                agg['pending'] += 1
            elif status == 'resolved-helpful':
                agg['resolved_helpful'] += 1
        if route:
            route_agg = delay_by_route.setdefault(route, {'pending': 0, 'resolved_helpful': 0})
            if status == 'pending':
                route_agg['pending'] += 1
            elif status == 'resolved-helpful':
                route_agg['resolved_helpful'] += 1

    for key, payload in outcomes.items():
        used = int(payload.get('used', 0) or 0)
        helpful = int(payload.get('helpful', 0) or 0)
        neutral = int(payload.get('neutral', 0) or 0)
        resisted = int(payload.get('resisted', 0) or 0)
        ignored = int(payload.get('ignored', 0) or 0)
        movement = int(payload.get('movement', 0) or 0)
        movement_small = int(payload.get('movement-small', 0) or 0)
        reflection_intent = int(payload.get('reflection-with-intent', 0) or 0)
        truthful_delay = int(payload.get('truthful-delay', 0) or 0)
        lazy_delay = int(payload.get('lazy-delay', 0) or 0)
        compliance_theater = int(payload.get('compliance-theater', 0) or 0)
        movement_theater = int(payload.get('movement-theater', 0) or 0)
        moral_posturing = int(payload.get('moral-posturing', 0) or 0)
        defensive_intelligence = int(payload.get('defensive-intelligence', 0) or 0)

        followthrough = movement + movement_small + reflection_intent
        theater = compliance_theater + movement_theater + moral_posturing + defensive_intelligence
        score = helpful * 2 + neutral - resisted * 2 - ignored + followthrough * 3 + truthful_delay - lazy_delay * 2 - theater * 3
        followthrough_ratio = round(followthrough / used, 3) if used else 0.0
        theater_ratio = round(theater / used, 3) if used else 0.0

        delay_stats = dict(delay_by_event.get(key) or {})
        pending_delay = int(delay_stats.get('pending', 0) or 0)
        resolved_delay = int(delay_stats.get('resolved_helpful', 0) or 0)
        delayed_followthrough_ratio = round(resolved_delay / (resolved_delay + pending_delay), 3) if (resolved_delay + pending_delay) else 0.0
        row = {
            'key': key,
            'used': used,
            'helpful': helpful,
            'neutral': neutral,
            'resisted': resisted,
            'ignored': ignored,
            'followthrough': followthrough,
            'truthful_delay': truthful_delay,
            'lazy_delay': lazy_delay,
            'theater': theater,
            'score': score,
            'followthrough_ratio': followthrough_ratio,
            'theater_ratio': theater_ratio,
            'pending_delayed_followthrough': pending_delay,
            'resolved_delayed_followthrough': resolved_delay,
            'delayed_followthrough_ratio': delayed_followthrough_ratio,
        }
        rows.append(row)

        total_followthrough += followthrough
        total_theater += theater
        total_truthful_delay += truthful_delay
        total_lazy_delay += lazy_delay

        if '::' in key:
            route, _event = key.split('::', 1)
            agg = route_rows.setdefault(route, {
                'route': route,
                'used': 0,
                'followthrough': 0,
                'theater': 0,
                'truthful_delay': 0,
                'lazy_delay': 0,
                'score': 0,
            })
            agg['used'] += used
            agg['followthrough'] += followthrough
            agg['theater'] += theater
            agg['truthful_delay'] += truthful_delay
            agg['lazy_delay'] += lazy_delay
            agg['score'] += score

    rows.sort(key=lambda x: (-x['score'], -x['followthrough'], x['key']))
    route_summary = []
    for agg in route_rows.values():
        used = int(agg.get('used', 0) or 0)
        delay_stats = dict(delay_by_route.get(agg.get('route', '')) or {})
        pending_delay = int(delay_stats.get('pending', 0) or 0)
        resolved_delay = int(delay_stats.get('resolved_helpful', 0) or 0)
        agg['followthrough_ratio'] = round(int(agg.get('followthrough', 0) or 0) / used, 3) if used else 0.0
        agg['theater_ratio'] = round(int(agg.get('theater', 0) or 0) / used, 3) if used else 0.0
        agg['pending_delayed_followthrough'] = pending_delay
        agg['resolved_delayed_followthrough'] = resolved_delay
        agg['delayed_followthrough_ratio'] = round(resolved_delay / (resolved_delay + pending_delay), 3) if (resolved_delay + pending_delay) else 0.0
        route_summary.append(agg)
    route_summary.sort(key=lambda x: (-x['score'], -x['followthrough_ratio'], x['route']))

    return {
        'best': rows[:5],
        'worst': sorted(rows, key=lambda x: (x['score'], -x['theater_ratio'], x['key']))[:5],
        'by_route': route_summary,
        'totals': {
            'followthrough': total_followthrough,
            'theater': total_theater,
            'truthful_delay': total_truthful_delay,
            'lazy_delay': total_lazy_delay,
            'pending_delayed_followthrough': len(pending_delays),
            'resolved_delayed_followthrough': len(resolved_helpful_delays),
        },
        'total_tracked': len(rows),
    }
