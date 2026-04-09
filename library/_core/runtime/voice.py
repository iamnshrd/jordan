"""Voice mode selection.

Restructured from: choose_voice_mode.py
"""
from library.config import USER_STATE, SESSION_STATE
from library.utils import load_json


def choose(question='', theme=''):
    """Return the appropriate voice mode name for the current context."""
    user = load_json(USER_STATE)
    session = load_json(SESSION_STATE)
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
