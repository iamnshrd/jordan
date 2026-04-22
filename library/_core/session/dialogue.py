"""Short-horizon dialogue state persistence."""
from __future__ import annotations

from library.config import canonical_user_id, get_default_store
from library._core.state_store import StateStore, KEY_DIALOGUE_STATE
from library.utils import now_iso


_DEFAULT_V1: dict = {
    'version': 1,
    'active_topic': '',
    'active_route': '',
    'active_problem_frame': '',
    'dialogue_mode': 'topic_opening',
    'abstraction_level': 'personal',
    'pending_slot': '',
    'last_clarify_profile': '',
    'last_question_kind': '',
    'last_reason_code': '',
    'last_user_turn': '',
    'last_system_turn': '',
    'last_turn_at': '',
    'turn_count_in_topic': 0,
    'topic_confidence': '',
    'candidate_axes': [],
}


def load(user_id: str = 'default', store: StateStore | None = None) -> dict:
    """Load the current dialogue state."""
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    data = store.get_json(user_id, KEY_DIALOGUE_STATE)
    if data:
        for key, default_val in _DEFAULT_V1.items():
            if key not in data:
                data[key] = list(default_val) if isinstance(default_val, list) else default_val
        return data
    return dict(_DEFAULT_V1)


def save(data: dict, *, user_id: str = 'default',
         store: StateStore | None = None) -> dict:
    """Persist the dialogue state."""
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    payload = dict(_DEFAULT_V1)
    payload.update(data or {})
    payload['last_turn_at'] = payload.get('last_turn_at') or now_iso()
    store.put_json(user_id, KEY_DIALOGUE_STATE, payload)
    return payload


def clear(user_id: str = 'default', store: StateStore | None = None) -> dict:
    """Reset dialogue state to defaults."""
    return save(dict(_DEFAULT_V1), user_id=user_id, store=store)
