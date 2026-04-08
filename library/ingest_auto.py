#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

ROOT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library')
INCOMING = ROOT / 'incoming'
BOOKS = ROOT / 'books'
ARTICLES = ROOT / 'articles'
TEXTS = ROOT / 'texts'
INGEST = ROOT / 'ingest_book.py'
BUILD = ROOT / 'build_kb.py'
EXTRACT = ROOT / 'extract_kb_candidates.py'
NORMALIZE = ROOT / 'normalize_kb_candidates.py'
WRITE = ROOT / 'write_kb_evidence.py'
EXTRACT_QUOTES = ROOT / 'extract_quotes.py'
NORMALIZE_QUOTES = ROOT / 'normalize_quotes.py'
LOAD_QUOTES = ROOT / 'load_quotes.py'
REPORT = ROOT / 'ingest_report.json'


def slugify(name):
    s = name.lower()
    out = []
    for ch in s:
        if ch.isalnum(): out.append(ch)
        elif ch in [' ', '-', '_', '.']: out.append('-')
    slug = ''.join(out)
    while '--' in slug:
        slug = slug.replace('--', '-')
    return slug.strip('-')


def classify_target(path):
    name = path.stem.lower()
    if any(x in name for x in ['article', 'essay', 'interview']):
        return ARTICLES
    return BOOKS


def main():
    processed = []
    skipped = []
    errors = []
    for path in sorted(INCOMING.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() != '.pdf':
            skipped.append({'file': path.name, 'reason': 'unsupported_suffix'})
            continue
        target_dir = classify_target(path)
        target_name = slugify(path.stem) + '.pdf'
        target = target_dir / target_name
        if target.exists():
            skipped.append({'file': path.name, 'reason': 'already_exists'})
            path.unlink()
            continue
        path.rename(target)
        text_name = target.stem + '.txt'
        text_path = TEXTS / text_name
        try:
            subprocess.check_call(['pdftotext', str(target), str(text_path)])
            subprocess.check_call(['python3', str(INGEST), target.name, text_name, 'text_extracted'])
            processed.append({'pdf': str(target.relative_to(ROOT)), 'text': str(text_path.relative_to(ROOT))})
        except subprocess.CalledProcessError as e:
            errors.append({'file': str(target.relative_to(ROOT)), 'error': str(e)})
    if processed:
        subprocess.check_call(['python3', str(BUILD)])
        subprocess.check_call(['python3', str(EXTRACT)])
        subprocess.check_call(['python3', str(NORMALIZE)])
        subprocess.check_call(['python3', str(WRITE)])
        subprocess.check_call(['python3', str(EXTRACT_QUOTES)])
        subprocess.check_call(['python3', str(NORMALIZE_QUOTES)])
        subprocess.check_call(['python3', str(LOAD_QUOTES)])
    report = {'processed': processed, 'skipped': skipped, 'errors': errors}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
