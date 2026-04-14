#!/usr/bin/env python3
"""DEPRECATED: Use ``python -m library respond`` instead."""
import sys, os, argparse, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.warn(
    'render_response.py is deprecated. Use: python -m library respond "question"',
    DeprecationWarning, stacklevel=2,
)
from library._core.runtime.respond import respond

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    args = ap.parse_args()
    print(respond(args.question))

if __name__ == '__main__':
    main()
