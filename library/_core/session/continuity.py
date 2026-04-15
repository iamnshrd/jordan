"""Continuity state -- load, update, summarize, migrate.

Merged from: read_continuity, update_continuity, continuity_summary,
             migrate_continuity_v2.
"""
from __future__ import annotations

from library.config import canonical_user_id, get_default_store
from library._core.state_store import (
    StateStore, KEY_CONTINUITY, KEY_CONTINUITY_SUMMARY,
)
from library.utils import now_iso


def _sort_items(items, key='salience'):
    return sorted(
        items,
        key=lambda x: (
            -x.get(key, 0),
            -x.get('count', 0),
            x.get('name', x.get('summary', '')),
        ),
    )


_DEFAULT_V3: dict = {
    'version': 3,
    'user_patterns': [],
    'recurring_themes': [],
    'open_loops': [],
    'resolved_loops': [],
    'identity_conflicts': [],
    'relationship_loops': [],
    'discipline_loops': [],
    'last_updated': None,
}


# -- persistence -----------------------------------------------------------

def load(user_id: str = 'default', store: StateStore | None = None):
    """Load continuity, returning v3-structure defaults when missing."""
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    data = store.get_json(user_id, KEY_CONTINUITY)
    if data:
        for key, default_val in _DEFAULT_V3.items():
            if data.get(key) is None:
                data[key] = default_val if not isinstance(default_val, list) else list(default_val)
            else:
                data.setdefault(key, default_val if not isinstance(default_val, list) else list(default_val))
        return data
    return dict(_DEFAULT_V3)


def save(data, user_id: str = 'default', store: StateStore | None = None):
    """Persist continuity with a refreshed last_updated timestamp."""
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    data['last_updated'] = now_iso()
    store.put_json(user_id, KEY_CONTINUITY, data)


# -- item helpers ----------------------------------------------------------

def bump_named(items, name, salience=1):
    """Increment or create a named item (theme / pattern)."""
    if not name:
        return
    for item in items:
        if item['name'] == name:
            item['count'] += 1
            item['salience'] += salience
            item['last_seen'] = now_iso()
            return
    items.append({
        'name': name,
        'count': 1,
        'salience': salience,
        'first_seen': now_iso(),
        'last_seen': now_iso(),
    })


def bump_loop(items, summary, salience=1, status='open'):
    """Increment or create a loop entry."""
    if not summary:
        return
    for item in items:
        if item['summary'] == summary:
            item['count'] += 1
            item['salience'] += salience
            item['status'] = status
            item['last_seen'] = now_iso()
            return
    items.append({
        'summary': summary,
        'status': status,
        'count': 1,
        'salience': salience,
        'first_seen': now_iso(),
        'last_seen': now_iso(),
    })


def route_bucket(data, theme, pattern, open_loop):
    """Route an observation into relationship / discipline / identity loops."""
    if theme == 'responsibility' and pattern == 'resentment-loop':
        bump_loop(
            data['relationship_loops'],
            open_loop or 'relationship resentment loop',
            2,
        )
    if pattern == 'avoidance-loop':
        bump_loop(
            data['discipline_loops'],
            open_loop or 'avoidance / discipline loop',
            2,
        )
    if theme == 'meaning':
        bump_loop(
            data['identity_conflicts'],
            open_loop or 'identity / meaning conflict',
            1,
        )


def resolve_loop(data, summary):
    """Mark an open loop as resolved and move it to resolved_loops."""
    if not summary:
        return
    for item in data.get('open_loops', []):
        if item['summary'] == summary:
            item['status'] = 'resolved'
            item['last_seen'] = now_iso()
            data.setdefault('resolved_loops', []).append(item)
            data['open_loops'] = [
                x for x in data['open_loops'] if x['summary'] != summary
            ]
            return


# -- main update -----------------------------------------------------------

def update(question, theme=None, pattern=None, open_loop=None,
           resolved_loop=None, user_id: str = 'default',
           store: StateStore | None = None):
    """Full continuity update cycle -- returns the updated data dict."""
    data = load(user_id=user_id, store=store)
    if data.get('version') != 3:
        data['version'] = 3
        data.setdefault('resolved_loops', [])
    bump_named(data['recurring_themes'], theme, 2 if theme else 1)
    bump_named(data['user_patterns'], pattern, 2 if pattern else 1)
    bump_loop(data['open_loops'], open_loop, 1)
    if resolved_loop:
        resolve_loop(data, resolved_loop)
    route_bucket(data, theme, pattern, open_loop)
    save(data, user_id=user_id, store=store)
    return data


# -- read (sorted top items) -----------------------------------------------

def read(user_id: str = 'default', store: StateStore | None = None):
    """Return continuity with top-5 sorted slices per bucket.

    Refreshes the summary cache if continuity data is newer.
    """
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    data = store.get_json(user_id, KEY_CONTINUITY)
    summary = store.get_json(user_id, KEY_CONTINUITY_SUMMARY)
    data_ts = data.get('last_updated', '')
    summary_ts = summary.get('last_updated', '')
    if data_ts and data_ts > summary_ts:
        return summarize(user_id=user_id, store=store)
    if summary and summary.get('top_themes') is not None:
        return summary
    return {
        'top_themes': _sort_items(data.get('recurring_themes', []))[:5],
        'top_patterns': _sort_items(data.get('user_patterns', []))[:5],
        'open_loops': _sort_items(data.get('open_loops', []))[:5],
        'identity_conflicts': _sort_items(
            data.get('identity_conflicts', []),
        )[:5],
        'relationship_loops': _sort_items(
            data.get('relationship_loops', []),
        )[:5],
        'discipline_loops': _sort_items(
            data.get('discipline_loops', []),
        )[:5],
        'last_updated': data.get('last_updated'),
    }


# -- summarize -------------------------------------------------------------

def summarize(user_id: str = 'default', store: StateStore | None = None):
    """Write continuity_summary and return the summary dict."""
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    data = store.get_json(user_id, KEY_CONTINUITY)
    summary = {
        'top_themes': _sort_items(data.get('recurring_themes', []))[:5],
        'top_patterns': _sort_items(data.get('user_patterns', []))[:5],
        'open_loops': _sort_items(data.get('open_loops', []))[:5],
        'resolved_loops': _sort_items(data.get('resolved_loops', []))[:5],
        'identity_conflicts': _sort_items(
            data.get('identity_conflicts', []),
        )[:5],
        'relationship_loops': _sort_items(
            data.get('relationship_loops', []),
        )[:5],
        'discipline_loops': _sort_items(
            data.get('discipline_loops', []),
        )[:5],
        'last_updated': data.get('last_updated'),
    }
    store.put_json(user_id, KEY_CONTINUITY_SUMMARY, summary)
    return summary


# -- migrate v1 -> v2 -----------------------------------------------------

def _wrap_name_list(values):
    out = []
    for v in values:
        out.append({
            'name': v,
            'count': 1,
            'salience': 1,
            'first_seen': now_iso(),
            'last_seen': now_iso(),
        })
    return out


def _wrap_open_loops(values):
    out = []
    for v in values:
        out.append({
            'summary': v,
            'status': 'open',
            'count': 1,
            'salience': 1,
            'first_seen': now_iso(),
            'last_seen': now_iso(),
        })
    return out


def migrate_v2(user_id: str = 'default', store: StateStore | None = None):
    """Migrate continuity from v1 (plain strings) to v2 (rich objects).

    Returns the migrated data or ``'already_v2'`` if nothing to do.
    """
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    old = store.get_json(user_id, KEY_CONTINUITY, default={
        'user_patterns': [],
        'recurring_themes': [],
        'open_loops': [],
        'last_updated': None,
    })
    if old.get('version') == 2:
        return 'already_v2'
    new = {
        'version': 2,
        'user_patterns': _wrap_name_list(old.get('user_patterns', [])),
        'recurring_themes': _wrap_name_list(old.get('recurring_themes', [])),
        'open_loops': _wrap_open_loops(old.get('open_loops', [])),
        'identity_conflicts': [],
        'relationship_loops': [],
        'discipline_loops': [],
        'last_updated': old.get('last_updated') or now_iso(),
    }
    store.put_json(user_id, KEY_CONTINUITY, new)
    return new
