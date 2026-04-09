#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.kb.seed import seed_v3_quality

if __name__ == '__main__':
    print(seed_v3_quality())
