#!/usr/bin/env python3
import sys, os, json, argparse, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.runtime.frame import select_frame

warnings.warn(
    'select_frame.py is deprecated. Use: python -m library frame "question"',
    DeprecationWarning, stacklevel=2,
)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    args = ap.parse_args()
    print(json.dumps(select_frame(args.question), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
