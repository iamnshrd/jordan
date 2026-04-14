#!/usr/bin/env python3
import sys, os, json, argparse, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.session.continuity import update

warnings.warn(
    'update_continuity.py is deprecated. Use StateStore API or python -m library run.',
    DeprecationWarning, stacklevel=2,
)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    ap.add_argument('--theme', default='')
    ap.add_argument('--pattern', default='')
    ap.add_argument('--open-loop', default='')
    ap.add_argument('--resolved-loop', default='')
    args = ap.parse_args()
    result = update(args.question, args.theme, args.pattern, getattr(args, 'open_loop', ''), getattr(args, 'resolved_loop', ''))
    print(json.dumps(result, ensure_ascii=False, indent=2))
