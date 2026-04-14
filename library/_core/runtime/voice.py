"""Voice mode selection.

Restructured from: choose_voice_mode.py
"""
from __future__ import annotations

from library.config import QUESTION_ARCHETYPES, get_default_store
from library._core.state_store import StateStore, KEY_USER_STATE, KEY_SESSION_STATE
from library.utils import load_json

_archetypes_cache: list | None = None


def _get_archetypes() -> list:
    global _archetypes_cache
    if _archetypes_cache is None:
        _archetypes_cache = load_json(QUESTION_ARCHETYPES, default=[])
    return _archetypes_cache


def choose(question='', theme=None, user_id: str = 'default',
           store: StateStore | None = None):
    """Return the appropriate voice mode name for the current context.

    Priority (highest → lowest):
    1. Session override (``current_voice_mode``) — explicit user/session choice
    2. Route-based bias (from canonical routes registry)
    3. Theme-based heuristic (suffering → reflective, truth → hard)
    4. Archetype-based bias (from question_archetypes.json)
    5. User profile recommendation (``recommended_voice``)
    6. Default
    """
    store = store or get_default_store()
    user = store.get_json(user_id, KEY_USER_STATE)
    session = store.get_json(user_id, KEY_SESSION_STATE)
    q = (question or '').lower()
    if theme is None:
        theme = session.get('working_theme', '')

    if session.get('current_voice_mode'):
        return session['current_voice_mode']

    from library._core.runtime.routes import infer_route, route_voice_bias
    route = infer_route(question)
    route_bias = route_voice_bias(route)
    if route_bias:
        return route_bias

    if theme == 'suffering':
        return 'reflective'
    if theme == 'truth':
        return 'hard'

    for arch in _get_archetypes():
        if any(x in q for x in arch.get('if_user_says', [])):
            bias = arch.get('voice_bias')
            if bias:
                return bias
            break

    if user.get('recommended_voice'):
        return user['recommended_voice']
    return 'default'
