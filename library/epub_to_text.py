#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.ingest.epub import convert

if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('Usage: epub_to_text.py <epub-unzipped-dir> <out.txt>')
    print(convert(sys.argv[1], sys.argv[2]))
