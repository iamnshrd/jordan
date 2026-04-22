"""Dialogue-frame persistence for adaptive conversational planning."""
from __future__ import annotations

from library._core.state_store import StateStore, KEY_DIALOGUE_FRAME
from library.config import canonical_user_id, get_default_store


_DEFAULT_V1: dict = {
    'version': 1,
    'topic': '',
    'route': '',
    'frame_type': '',
    'stance': 'personal',
    'goal': 'opening',
    'axis': '',
    'detail': '',
    'pending_slot': '',
    'relation_to_previous': 'new',
    'confidence': '',
}


def load(user_id: str = 'default', store: StateStore | None = None) -> dict:
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    data = store.get_json(user_id, KEY_DIALOGUE_FRAME)
    if data:
        payload = dict(_DEFAULT_V1)
        payload.update(data)
        return payload
    return dict(_DEFAULT_V1)


def save(data: dict, *, user_id: str = 'default',
         store: StateStore | None = None) -> dict:
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    payload = dict(_DEFAULT_V1)
    payload.update(data or {})
    store.put_json(user_id, KEY_DIALOGUE_FRAME, payload)
    return payload


def clear(user_id: str = 'default', store: StateStore | None = None) -> dict:
    return save(dict(_DEFAULT_V1), user_id=user_id, store=store)
