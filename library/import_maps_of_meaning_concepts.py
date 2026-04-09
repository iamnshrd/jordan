#!/usr/bin/env python3
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.kb.concepts import import_maps_of_meaning

if __name__ == '__main__':
    print(json.dumps(import_maps_of_meaning(), ensure_ascii=False, indent=2))
