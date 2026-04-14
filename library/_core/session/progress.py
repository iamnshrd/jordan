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

    topic_keywords: list[str] = []
    if question:
        q = question.lower()
        for kw in ['карьер', 'призвание', 'стыд', 'отношен', 'хаос',
                    'зависим', 'ребен', 'воспит']:
            if kw in q:
                topic_keywords.append(kw)

    if question:
        same = [c for c in checkpoints if c.get('question') == question]
        if not same and topic_keywords:
            for c in checkpoints:
                cq = (c.get('question') or '').lower()
                if any(x in cq for x in topic_keywords):
                    same.append(c)
    else:
        same = checkpoints[-3:]

    from library.utils import get_threshold
    repeat_count = len(same)

    all_resolved = cont.get('resolved_loops') or []
    if topic_keywords:
        resolved_count = sum(
            1 for r in all_resolved
            if isinstance(r, dict) and any(
                kw in (r.get('summary') or '').lower() for kw in topic_keywords
            )
        )
    elif repeat_count > 0:
        recent_resolved = all_resolved[-3:] if all_resolved else []
        resolved_count = len(recent_resolved)
    else:
        resolved_count = 0
    stuckness_score = max(0, repeat_count * 2 - resolved_count)

    stuck_threshold = get_threshold('progress_repeat_stuck_threshold', 3)
    if repeat_count >= stuck_threshold and resolved_count == 0:
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
