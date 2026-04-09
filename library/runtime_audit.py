#!/usr/bin/env python3
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.eval.audit import audit

if __name__ == '__main__':
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
