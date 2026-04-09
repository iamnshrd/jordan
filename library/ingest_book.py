#!/usr/bin/env python3
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library._core.ingest.book import register

if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit('Usage: ingest_book.py <pdf-filename> [text-filename] [status]')
    pdf_name = sys.argv[1]
    text_name = sys.argv[2] if len(sys.argv) >= 3 else None
    status = sys.argv[3] if len(sys.argv) >= 4 else ('text_extracted' if text_name else 'pending_text_extraction')
    print(json.dumps(register(pdf_name, text_name, status), ensure_ascii=False, indent=2))
