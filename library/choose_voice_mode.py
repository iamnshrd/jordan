#!/usr/bin/env python3
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.runtime.voice import choose

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('question', nargs='?', default='')
    ap.add_argument('--theme', default='')
    args = ap.parse_args()
    print(choose(args.question, args.theme))

if __name__ == '__main__':
    main()
