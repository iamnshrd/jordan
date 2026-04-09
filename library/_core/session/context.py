"""Context-graph assembly.

Refactored from: assemble_context_graph.
"""
from library.config import CONTINUITY, SESSION_STATE, EFFECTIVENESS, CONTEXT_GRAPH
from library.utils import load_json, save_json


def assemble():
    """Build context graph from continuity, session state, and effectiveness.

    Writes context_graph.json and returns the graph dict.
    """
    cont = load_json(CONTINUITY)
    session = load_json(SESSION_STATE)
    effect = load_json(EFFECTIVENESS)

    graph = {
        'theme_links': [],
        'pattern_links': [],
        'source_links': [],
        'session': session,
    }

    themes = [
        x.get('name')
        for x in cont.get('recurring_themes', [])[:5]
        if isinstance(x, dict)
    ]
    patterns = [
        x.get('name')
        for x in cont.get('user_patterns', [])[:5]
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

    save_json(CONTEXT_GRAPH, graph)
    return graph
