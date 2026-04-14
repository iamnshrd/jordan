"""User-reaction estimation.

Refactored from: estimate_user_reaction.
"""
from __future__ import annotations

from library.config import get_default_store
from library._core.state_store import (
    StateStore, KEY_CHECKPOINTS, KEY_REACTION_ESTIMATE,
)


def estimate(question='', user_id: str = 'default',
             store: StateStore | None = None):
    """Estimate user reaction from recent checkpoints.

    Writes user_reaction_estimate and returns the result dict.
    """
    store = store or get_default_store()
    rows = store.read_jsonl(user_id, KEY_CHECKPOINTS)

    if question:
        q_norm = ' '.join(question.lower().split())
        q_words = set(q_norm.split())
        recent = [r for r in rows if r.get('question') == question][-3:]
        if not recent and q_words:
            for r in rows:
                rq = ' '.join((r.get('question') or '').lower().split())
                rq_words = set(rq.split())
                if q_words and rq_words:
                    overlap = len(q_words & rq_words) / max(len(q_words), 1)
                    if overlap >= 0.6:
                        recent.append(r)
            recent = recent[-3:]
    else:
        recent = rows[-3:]

    if not recent:
        result = {'question': question, 'user_reaction_estimate': 'unknown'}
    else:
        if any(r.get('movement_estimate') == 'moving' for r in recent):
            reaction = 'accepting'
        elif all(r.get('movement_estimate') == 'stuck' for r in recent):
            reaction = 'resisting'
        else:
            reaction = 'ambiguous'
        result = {'question': question, 'user_reaction_estimate': reaction}

    store.put_json(user_id, KEY_REACTION_ESTIMATE, result)
    return result
