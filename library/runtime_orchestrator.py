#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

SELECT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/select_frame.py')
RESPOND = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/respond_with_kb.py')
READ_CONT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/read_continuity.py')


def run_json(cmd):
    return json.loads(subprocess.check_output(cmd, text=True))


def detect_mode(question):
    q = question.lower()
    if len(q) < 80:
        return 'quick'
    if any(x in q for x in ['что мне делать', 'что делать', 'next step', 'практически']):
        return 'practical'
    return 'deep'


def should_use_kb(question):
    q = question.lower()
    triggers = ['смысл', 'дисциплин', 'обид', 'стыд', 'отношен', 'конфликт', 'карьер', 'призвание', 'хаос', 'вру', 'самообман']
    return any(t in q for t in triggers)


def orchestrate(question):
    mode = detect_mode(question)
    if not should_use_kb(question):
        return {
            'question': question,
            'mode': mode,
            'use_kb': False,
            'confidence': 'low',
            'action': 'answer-directly',
            'reason': 'Question does not strongly match psychological/philosophical KB routes.',
            'continuity': run_json(['python3', str(READ_CONT)]),
        }
    selected = run_json(['python3', str(SELECT), question])
    confidence = selected.get('confidence', 'low')
    continuity = run_json(['python3', str(READ_CONT)])
    if confidence == 'low':
        return {
            'question': question,
            'mode': mode,
            'use_kb': True,
            'confidence': confidence,
            'action': 'ask-clarifying-question',
            'reason': 'KB route is weak; clarification preferred before forcing a frame.',
            'selection': selected,
            'continuity': continuity,
        }
    response = subprocess.check_output(['python3', str(RESPOND), question, '--mode', mode if mode in {'quick','deep'} else 'deep'], text=True)
    return {
        'question': question,
        'mode': mode,
        'use_kb': True,
        'confidence': confidence,
        'action': 'respond-with-kb',
        'selection': selected,
        'continuity': continuity,
        'response': response,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    args = ap.parse_args()
    print(json.dumps(orchestrate(args.question), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
