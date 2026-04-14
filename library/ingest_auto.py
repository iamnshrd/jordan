#!/usr/bin/env python3
import sys, os, json, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.ingest.auto import ingest

warnings.warn(
    'ingest_auto.py is deprecated. Use: python -m library ingest auto',
    DeprecationWarning, stacklevel=2,
)

if __name__ == '__main__':
    print(json.dumps(ingest(), ensure_ascii=False, indent=2))
