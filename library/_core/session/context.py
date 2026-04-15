"""Context-graph assembly.

Refactored from: assemble_context_graph.
"""
from __future__ import annotations

from library.config import canonical_user_id, get_default_store
from library._core.state_store import (
    StateStore, KEY_CONTINUITY, KEY_SESSION_STATE,
    KEY_EFFECTIVENESS, KEY_CONTEXT_GRAPH,
)


def assemble(user_id: str = 'default', store: StateStore | None = None):
    """Build context graph from continuity, session state, and effectiveness.

    Writes context_graph and returns the graph dict.
    """
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    cont = store.get_json(user_id, KEY_CONTINUITY)
    session = store.get_json(user_id, KEY_SESSION_STATE)
    effect = store.get_json(user_id, KEY_EFFECTIVENESS)

    graph: dict = {
        'theme_links': [],
        'pattern_links': [],
        'source_links': [],
        'session': session,
    }

    themes = [
        x.get('name')
        for x in (cont.get('recurring_themes') or [])[:5]
        if isinstance(x, dict)
    ]
    patterns = [
        x.get('name')
        for x in (cont.get('user_patterns') or [])[:5]
        if isinstance(x, dict)
    ]

    for t in themes:
        for p in patterns:
            graph['theme_links'].append({'theme': t, 'pattern': p})

    current_source = session.get('current_source_blend', '')
    if current_source:
        parts = [x for x in current_source.split('->') if x]
        for src in parts:
            graph['source_links'].append({
                'source': src,
                'times_used': (
                    effect
                    .get('sources', {})
                    .get(src, {})
                    .get('times_used', 0)
                ),
            })

    store.put_json(user_id, KEY_CONTEXT_GRAPH, graph)
    return graph
