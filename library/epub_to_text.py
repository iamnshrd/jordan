#!/usr/bin/env python3
import re
import sys
from pathlib import Path
from html import unescape

TAG_RE = re.compile(r'<[^>]+>')
WS_RE = re.compile(r'[ \t\r\f\v]+')
TITLE_RE = re.compile(r'<title>(.*?)</title>', re.IGNORECASE | re.DOTALL)
BODY_RE = re.compile(r'<body.*?>(.*)</body>', re.IGNORECASE | re.DOTALL)


def clean_html(text: str) -> str:
    m = BODY_RE.search(text)
    if m:
        text = m.group(1)
    text = re.sub(r'<script.*?</script>', ' ', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<style.*?</style>', ' ', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'</(p|div|section|article|h1|h2|h3|h4|h5|h6|li|tr|blockquote)>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = TAG_RE.sub(' ', text)
    text = unescape(text)
    text = text.replace('\xa0', ' ')
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = '\n'.join(line.strip() for line in text.splitlines())
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = '\n'.join(WS_RE.sub(' ', line).strip() for line in text.splitlines())
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def main(root_dir: str, out_path: str):
    root = Path(root_dir)
    files = sorted([p for p in root.rglob('*') if p.suffix.lower() in {'.xhtml', '.html', '.htm'}])
    out = []
    for p in files:
        raw = p.read_text(errors='ignore')
        text = clean_html(raw)
        if len(text) < 50:
            continue
        out.append(f"\n\n# FILE: {p.name}\n\n{text}\n")
    Path(out_path).write_text('\n'.join(out))
    print(out_path)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('Usage: epub_to_text.py <epub-unzipped-dir> <out.txt>')
    main(sys.argv[1], sys.argv[2])
