#!/usr/bin/env python3
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.runtime.respond import respond

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    ap.add_argument('--mode', choices=['quick', 'practical', 'deep'], default='deep')
    ap.add_argument('--voice', choices=['default', 'concise', 'hard', 'reflective'], default='default')
    args = ap.parse_args()
    print(respond(args.question, mode=args.mode, voice=args.voice))

if __name__ == '__main__':
    main()
