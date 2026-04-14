#!/usr/bin/env python3
import sys, os, json, argparse, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.runtime.retrieve import build_response_bundle

warnings.warn(
    'retrieve_for_prompt.py is deprecated. Use: python -m library retrieve "question"',
    DeprecationWarning, stacklevel=2,
)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    args = ap.parse_args()
    print(json.dumps(build_response_bundle(args.question), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
