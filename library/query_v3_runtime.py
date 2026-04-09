#!/usr/bin/env python3
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.kb.query_v3 import query_v3

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--theme', default='')
    ap.add_argument('--pattern', default='')
    ap.add_argument('--archetype', default='')
    args = ap.parse_args()
    print(json.dumps(query_v3(args.theme, args.pattern, args.archetype), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
