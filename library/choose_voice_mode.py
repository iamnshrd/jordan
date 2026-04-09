#!/usr/bin/env python3
import json
from pathlib import Path

USER_STATE = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/user_state.json')
SESSION = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/session_state.json')


def load(path):
    if path.exists():
        return json.loads(path.read_text())
    return {}


def choose(question='', theme=''):
    user = load(USER_STATE)
    session = load(SESSION)
    q = question.lower()
    theme = theme or session.get('working_theme', '')
    if theme == 'suffering' or any(x in q for x in ['стыд', 'позор', 'отвращение к себе']):
        return 'reflective'
    if theme == 'truth' or any(x in q for x in ['вру', 'самообман', 'ложь']):
        return 'hard'
    if session.get('current_voice_mode'):
        return session['current_voice_mode']
    if user.get('recommended_voice'):
        return user['recommended_voice']
    return 'default'


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('question', nargs='?', default='')
    ap.add_argument('--theme', default='')
    args = ap.parse_args()
    print(choose(args.question, args.theme))
