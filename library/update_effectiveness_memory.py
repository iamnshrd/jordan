#!/usr/bin/env python3
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.session.effectiveness import update

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default='')
    ap.add_argument('--intervention', default='')
    ap.add_argument('--outcome', default='used')
    ap.add_argument('--route', default='')
    args = ap.parse_args()
    print(json.dumps(update(args.source, args.intervention, args.outcome, args.route), ensure_ascii=False, indent=2))
