#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.kb.migrate import migrate_v31

if __name__ == '__main__':
    print(migrate_v31())
