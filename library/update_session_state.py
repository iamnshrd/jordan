#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

STATE = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/session_state.json')


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def main(question, theme='', pattern='', principle='', source_blend='', voice='default', goal=''):
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
    STATE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    ap.add_argument('--theme', default='')
    ap.add_argument('--pattern', default='')
    ap.add_argument('--principle', default='')
    ap.add_argument('--source-blend', default='')
    ap.add_argument('--voice', default='default')
    ap.add_argument('--goal', default='')
    args = ap.parse_args()
    main(args.question, args.theme, args.pattern, args.principle, args.source_blend, args.voice, args.goal)
