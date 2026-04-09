#!/usr/bin/env python3
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.kb.quotes import load_quotes

if __name__ == '__main__':
    print(json.dumps(load_quotes(), ensure_ascii=False, indent=2))
