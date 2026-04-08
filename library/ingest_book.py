#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library')
BOOKS = ROOT / 'books'
TEXTS = ROOT / 'texts'
MANIFEST = ROOT / 'manifest.json'

TEXTS.mkdir(parents=True, exist_ok=True)


def load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {'documents': []}


def save_manifest(data):
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def register(pdf_name, text_name=None, status='pending_text_extraction'):
    pdf = BOOKS / pdf_name
    if not pdf.exists():
        raise SystemExit(f'Book not found: {pdf}')
    manifest = load_manifest()
    rel_text = f'texts/{text_name}' if text_name else None
    for entry in manifest['documents']:
        if entry.get('source_pdf') == str(pdf.relative_to(ROOT)):
            entry['text_path'] = rel_text
            entry['status'] = status
            save_manifest(manifest)
            print(json.dumps(entry, ensure_ascii=False, indent=2))
            return
    entry = {
        'source_pdf': str(pdf.relative_to(ROOT)),
        'text_path': rel_text,
        'status': status
    }
    manifest['documents'].append(entry)
    save_manifest(manifest)
    print(json.dumps(entry, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit('Usage: ingest_book.py <pdf-filename> [text-filename] [status]')
    pdf_name = sys.argv[1]
    text_name = sys.argv[2] if len(sys.argv) >= 3 else None
    status = sys.argv[3] if len(sys.argv) >= 4 else ('text_extracted' if text_name else 'pending_text_extraction')
    register(pdf_name, text_name, status)
