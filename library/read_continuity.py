#!/usr/bin/env python3
import sys, os, json, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.session.continuity import read

warnings.warn(
    'read_continuity.py is deprecated. Use StateStore API or python -m library run.',
    DeprecationWarning, stacklevel=2,
)

if __name__ == '__main__':
    print(json.dumps(read(), ensure_ascii=False, indent=2))
