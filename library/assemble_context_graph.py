#!/usr/bin/env python3
import json
from pathlib import Path

CONT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/continuity.json')
SESSION = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/session_state.json')
EFFECT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/effectiveness_memory.json')
OUT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/context_graph.json')


def load(path):
    if path.exists():
        return json.loads(path.read_text())
    return {}


def main():
    cont = load(CONT)
    session = load(SESSION)
    effect = load(EFFECT)
    graph = {
        'theme_links': [],
        'pattern_links': [],
        'source_links': [],
        'session': session,
    }
    themes = [x.get('name') for x in cont.get('recurring_themes', [])[:5] if isinstance(x, dict)]
    patterns = [x.get('name') for x in cont.get('user_patterns', [])[:5] if isinstance(x, dict)]
    for t in themes:
        for p in patterns:
            graph['theme_links'].append({'theme': t, 'pattern': p})
    current_source = session.get('current_source_blend', '')
    if current_source:
        parts = [x for x in current_source.split('->') if x]
        for src in parts:
            graph['source_links'].append({
                'source': src,
                'times_used': effect.get('sources', {}).get(src, {}).get('times_used', 0)
            })
    OUT.write_text(json.dumps(graph, ensure_ascii=False, indent=2))
    print(json.dumps(graph, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
