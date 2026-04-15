"""Effectiveness memory tracking.

Refactored from: update_effectiveness_memory.
"""
from __future__ import annotations

from library.config import canonical_user_id, get_default_store
from library._core.state_store import StateStore, KEY_EFFECTIVENESS
from library.utils import now_iso


def _bump(store_dict, key, outcome='used', route=''):
    row = store_dict.get(key, {})
    row.setdefault('times_used', 0)
    row.setdefault('times_helpful', 0)
    row.setdefault('times_neutral', 0)
    row.setdefault('times_unhelpful', 0)
    row.setdefault('times_resisted', 0)
    row.setdefault('times_abandoned', 0)
    row.setdefault('last_used', None)
    row.setdefault('last_route', '')
    row.setdefault('best_routes', [])
    row['times_used'] += 1
    if outcome == 'helpful':
        row['times_helpful'] += 1
    elif outcome == 'neutral':
        row['times_neutral'] += 1
    elif outcome == 'unhelpful':
        row['times_unhelpful'] += 1
    elif outcome == 'resisted':
        row['times_resisted'] += 1
    elif outcome == 'abandoned':
        row['times_abandoned'] += 1
    row['last_used'] = now_iso()
    if route:
        row['last_route'] = route
        if (
            row['times_helpful']
            > max(row['times_resisted'], row['times_unhelpful'])
            and route not in row['best_routes']
        ):
            row['best_routes'].append(route)
    store_dict[key] = row


def update(source='', intervention='', outcome='used', route='',
           user_id: str = 'default', store: StateStore | None = None):
    """Bump effectiveness counters for a source and/or intervention.

    Returns the full effectiveness data dict.
    """
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    data = store.get_json(user_id, KEY_EFFECTIVENESS, default={
        'sources': {},
        'interventions': {},
        'source_routes': {},
        'intervention_routes': {},
        'updated_at': None,
    })
    data.setdefault('source_routes', {})
    data.setdefault('intervention_routes', {})

    if source:
        _bump(data['sources'], source, outcome=outcome, route=route)
        if route:
            key = f'{source}::{route}'
            _bump(data['source_routes'], key, outcome=outcome, route=route)
    if intervention:
        _bump(data['interventions'], intervention, outcome=outcome, route=route)
        if route:
            key = f'{intervention}::{route}'
            _bump(
                data['intervention_routes'], key,
                outcome=outcome, route=route,
            )

    data['updated_at'] = now_iso()
    store.put_json(user_id, KEY_EFFECTIVENESS, data)
    try:
        from library._core.runtime.retrieve import invalidate_route_strength_cache
        invalidate_route_strength_cache()
    except ImportError:
        pass
    return data
