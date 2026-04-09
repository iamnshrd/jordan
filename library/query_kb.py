#!/usr/bin/env python3
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.kb.query import query

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--query', default='')
    ap.add_argument('--limit', type=int, default=8)
    ap.add_argument('--table', default='')
    args = ap.parse_args()
    print(json.dumps(query(args.query, args.table, args.limit), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
