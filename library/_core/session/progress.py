"""Progress-state estimation.

Refactored from: estimate_progress_state.
"""
from __future__ import annotations

from library.config import get_default_store
from library._core.state_store import (
    StateStore, KEY_CHECKPOINTS, KEY_CONTINUITY_SUMMARY, KEY_PROGRESS_STATE,
)


def estimate(question='', user_id: str = 'default',
             store: StateStore | None = None):
    """Compute progress state from checkpoints + continuity summary.

    Writes progress_state and returns the result dict.
    """
    store = store or get_default_store()
    checkpoints = store.read_jsonl(user_id, KEY_CHECKPOINTS)
    cont = store.get_json(user_id, KEY_CONTINUITY_SUMMARY)

    if question:
        same = [c for c in checkpoints if c.get('question') == question]
    else:
        same = checkpoints[-3:]

    if not same and question:
        q = question.lower()
        for c in checkpoints:
            cq = (c.get('question') or '').lower()
            if any(
                x in q and x in cq
                for x in ['карьер', 'призвание', 'стыд', 'отношен', 'хаос']
            ):
                same.append(c)

    repeat_count = len(same)
    resolved_count = len(cont.get('resolved_loops', []))
    stuckness_score = max(0, repeat_count * 2 - resolved_count)

    if repeat_count >= 3 and resolved_count == 0:
        state = 'stuck'
        recommended = 'hard'
    elif resolved_count >= 1:
        state = 'moving'
        recommended = 'reflective'
    else:
        state = 'fragile'
        recommended = 'default'

    out = {
        'question': question,
        'repeat_count': repeat_count,
        'resolved_count': resolved_count,
        'stuckness_score': stuckness_score,
        'progress_state': state,
        'recommended_voice_override': recommended,
        'recommended_response_mode': 'narrow' if state == 'stuck' else 'normal',
    }
    store.put_json(user_id, KEY_PROGRESS_STATE, out)
    return out
