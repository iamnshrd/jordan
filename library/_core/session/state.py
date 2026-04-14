"""Session state & user profile.

Merged from: update_session_state, user_state_profile.
"""
from __future__ import annotations

from library.config import get_default_store
from library._core.state_store import (
    StateStore, KEY_SESSION_STATE, KEY_USER_STATE, KEY_CONTINUITY,
)
from library.utils import now_iso


def update_session(question, theme='', pattern='', principle='',
                   source_blend='', voice='default', goal='',
                   user_id: str = 'default',
                   store: StateStore | None = None):
    """Write session_state with the current turn context.

    Returns the data dict written to disk.
    """
    store = store or get_default_store()
    data = {
        'question': question,
        'working_theme': theme,
        'working_pattern': pattern,
        'working_principle': principle,
        'current_source_blend': source_blend,
        'current_voice_mode': voice,
        'session_goal': goal,
        'updated_at': now_iso(),
    }
    store.put_json(user_id, KEY_SESSION_STATE, data)
    return data


def _top_name(items):
    dicts = [x for x in items if isinstance(x, dict)]
    if not dicts:
        return None
    dicts = sorted(
        dicts,
        key=lambda x: (-x.get('salience', 0), -x.get('count', 0)),
    )
    return dicts[0].get('name') or dicts[0].get('summary')


def build_user_profile(user_id: str = 'default',
                       store: StateStore | None = None):
    """Derive user_state from continuity.  Returns the profile dict."""
    store = store or get_default_store()
    data = store.get_json(user_id, KEY_CONTINUITY)
    open_loops = data.get('open_loops') or []
    resolved = data.get('resolved_loops') or []
    recurring_themes = data.get('recurring_themes') or []
    user_patterns = data.get('user_patterns') or []
    profile = {
        'dominant_loop': _top_name(open_loops),
        'dominant_theme': _top_name(recurring_themes),
        'dominant_pattern': _top_name(user_patterns),
        'instability_level': (
            'high' if len(open_loops) >= 4
            else 'medium' if len(open_loops) >= 2
            else 'low'
        ),
        'recent_resolved_count': len(resolved),
        'directness_preference': 'high',
        'confrontation_tolerance': 'medium',
        'recommended_voice': (
            'reflective'
            if _top_name(recurring_themes) == 'suffering'
            else 'default'
        ),
    }
    store.put_json(user_id, KEY_USER_STATE, profile)
    return profile
