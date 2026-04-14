#!/usr/bin/env python3
import sys, os, json, argparse, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.session.progress import estimate

warnings.warn(
    'estimate_progress_state.py is deprecated. Use StateStore API or python -m library run.',
    DeprecationWarning, stacklevel=2,
)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('question', nargs='?', default='')
    args = ap.parse_args()
    print(json.dumps(estimate(args.question), ensure_ascii=False, indent=2))
