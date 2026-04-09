#!/usr/bin/env python3
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.session.continuity import migrate_v2

if __name__ == '__main__':
    result = migrate_v2()
    print(json.dumps(result, ensure_ascii=False, indent=2) if isinstance(result, dict) else result)
