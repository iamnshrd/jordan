"""Automatic mentor tick entrypoint.

Evaluates whether a mentor follow-up should be sent and records the event when
asked to do so.
"""

from __future__ import annotations

from library._core.mentor.checkins import evaluate, record_sent
from library._core.mentor.delivery import prepare_delivery
from library._core.state_store import StateStore
from library.config import canonical_user_id


def tick(question: str = '', *, user_id: str = 'default', send: bool = False,
         store: StateStore | None = None) -> dict:
    user_id = canonical_user_id(user_id)
    result = evaluate(question, user_id=user_id, store=store)
    event = result.get('selected_event')
    delivery = prepare_delivery(result, user_id=user_id, store=store)
    result['mentor_delivery'] = delivery
    result['rendered_message'] = delivery.get('rendered_message', '')
    result['should_send'] = bool(delivery.get('should_send'))
    result['delivery_path_type'] = delivery.get('delivery_path_type', '')
    result['delivery_trace_id'] = delivery.get('trace_id', '')
    result['suppressed_reason'] = delivery.get('suppressed_reason', '')
    result['target_user_id'] = user_id
    if send and result['should_send']:
        record_sent(event, user_id=user_id, store=store)
        result['sent'] = True
    else:
        result['sent'] = False
    return result
