"""Automatic mentor tick entrypoint.

Evaluates whether a mentor follow-up should be sent and records the event when
asked to do so.
"""

from __future__ import annotations

from library._core.mentor.checkins import evaluate, record_sent
from library._core.mentor.render import render_event
from library._core.state_store import StateStore
from library.config import canonical_user_id


def tick(question: str = '', *, user_id: str = 'default', send: bool = False,
         store: StateStore | None = None) -> dict:
    user_id = canonical_user_id(user_id)
    result = evaluate(question, user_id=user_id, store=store)
    event = result.get('selected_event')
    rendered = render_event(event or {}) if event and not result.get('skip') else ''
    result['rendered_message'] = rendered
    result['should_send'] = bool(event and not result.get('skip') and rendered)
    result['target_user_id'] = user_id
    if send and result['should_send']:
        record_sent(event, user_id=user_id, store=store)
        result['sent'] = True
    else:
        result['sent'] = False
    return result
