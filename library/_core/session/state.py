"""Session state & user profile.

Merged from: update_session_state, user_state_profile.
"""
from library.config import SESSION_STATE, USER_STATE, CONTINUITY
from library.utils import now_iso, load_json, save_json


def update_session(question, theme='', pattern='', principle='',
                   source_blend='', voice='default', goal=''):
    """Write session_state.json with the current turn context.

    Returns the data dict written to disk.
    """
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
    save_json(SESSION_STATE, data)
    return data


def _top_name(items):
    if not items:
        return None
    items = sorted(
        items,
        key=lambda x: (-x.get('salience', 0), -x.get('count', 0)),
    )
    return items[0].get('name') or items[0].get('summary')


def build_user_profile():
    """Derive user_state.json from continuity.  Returns the profile dict."""
    data = load_json(CONTINUITY)
    open_loops = data.get('open_loops', [])
    resolved = data.get('resolved_loops', [])
    profile = {
        'dominant_loop': _top_name(open_loops),
        'dominant_theme': _top_name(data.get('recurring_themes', [])),
        'dominant_pattern': _top_name(data.get('user_patterns', [])),
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
            if _top_name(data.get('recurring_themes', [])) == 'suffering'
            else 'default'
        ),
    }
    save_json(USER_STATE, profile)
    return profile
