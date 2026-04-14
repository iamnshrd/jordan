"""Voice mode selection.

Restructured from: choose_voice_mode.py
"""
from __future__ import annotations

from library.config import get_default_store
from library._core.state_store import StateStore, KEY_USER_STATE, KEY_SESSION_STATE


def choose(question='', theme='', user_id: str = 'default',
           store: StateStore | None = None):
    """Return the appropriate voice mode name for the current context."""
    store = store or get_default_store()
    user = store.get_json(user_id, KEY_USER_STATE)
    session = store.get_json(user_id, KEY_SESSION_STATE)
    q = question.lower()
    theme = theme or session.get('working_theme', '')

    if theme == 'suffering' or any(x in q for x in ['стыд', 'позор',
                                                      'отвращение к себе']):
        return 'reflective'
    if theme == 'truth' or any(x in q for x in ['вру', 'самообман', 'ложь']):
        return 'hard'
    if session.get('current_voice_mode'):
        return session['current_voice_mode']
    if user.get('recommended_voice'):
        return user['recommended_voice']
    return 'default'
