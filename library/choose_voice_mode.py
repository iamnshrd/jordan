#!/usr/bin/env python3
import sys, os, argparse, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.runtime.voice import choose

warnings.warn(
    'choose_voice_mode.py is deprecated. Use: python -m library run "question"',
    DeprecationWarning, stacklevel=2,
)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('question', nargs='?', default='')
    ap.add_argument('--theme', default='')
    args = ap.parse_args()
    print(choose(args.question, args.theme))

if __name__ == '__main__':
    main()
