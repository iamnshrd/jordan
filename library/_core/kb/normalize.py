#!/usr/bin/env python3
"""Normalize KB candidates: filter noise, deduplicate."""
from library.config import KB_CANDIDATES, KB_CANDIDATES_NORM
from library.utils import load_json, save_json

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


def normalize():
    """Main normalization. Returns dict with counts."""
    data = load_json(KB_CANDIDATES, default={})
    out = {}
    out['themes'] = dedupe([x for x in data.get('themes', []) if keep(x)], 'theme_name')
    out['principles'] = dedupe([x for x in data.get('principles', []) if keep(x)], 'principle_name')
    out['patterns'] = dedupe([x for x in data.get('patterns', []) if keep(x)], 'pattern_name')
    save_json(KB_CANDIDATES_NORM, out)
    return {k: len(v) for k, v in out.items()}
