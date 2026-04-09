#!/usr/bin/env python3
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.session.state import update_session

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    ap.add_argument('--theme', default='')
    ap.add_argument('--pattern', default='')
    ap.add_argument('--principle', default='')
    ap.add_argument('--source-blend', default='')
    ap.add_argument('--voice', default='default')
    ap.add_argument('--goal', default='')
    args = ap.parse_args()
    result = update_session(args.question, args.theme, args.pattern, args.principle, getattr(args, 'source_blend', ''), args.voice, args.goal)
    print(json.dumps(result, ensure_ascii=False, indent=2))
