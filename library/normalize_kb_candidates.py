#!/usr/bin/env python3
import json
from pathlib import Path

SRC = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/kb_candidates.json')
OUT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/kb_candidates_normalized.json')


STOP_SNIPPETS = [
    'isbn',
    'удк',
    'ббк',
    'предисловие',
    'вступление',
    'правило 1.',
    'правило 2.',
    'оглавление',
]


def keep(item):
    text = (item.get('excerpt') or '').lower()
    if len(text) < 160:
        return False
    if any(s in text for s in STOP_SNIPPETS):
        return False
    return True


def dedupe(items, key_name):
    seen = set()
    out = []
    for item in items:
        key = (item.get(key_name), item.get('chunk_id'))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def main():
    data = json.loads(SRC.read_text())
    out = {}
    out['themes'] = dedupe([x for x in data.get('themes', []) if keep(x)], 'theme_name')
    out['principles'] = dedupe([x for x in data.get('principles', []) if keep(x)], 'principle_name')
    out['patterns'] = dedupe([x for x in data.get('patterns', []) if keep(x)], 'pattern_name')
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps({k: len(v) for k, v in out.items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
