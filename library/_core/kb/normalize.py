#!/usr/bin/env python3
"""Normalize KB candidates: filter noise, deduplicate."""
from library.config import KB_CANDIDATES, KB_CANDIDATES_NORM, COMMON_STOP_SNIPPETS
from library.utils import load_json, save_json

STOP_SNIPPETS = COMMON_STOP_SNIPPETS + [
    'правило 1.',
    'правило 2.',
]


def keep(item):
    from library.utils import get_threshold
    text = (item.get('excerpt') or '').lower()
    if len(text) < get_threshold('normalize_min_excerpt_length', 160):
        return False
    if any(s in text for s in STOP_SNIPPETS):
        return False
    return True


def dedupe(items, key_name):
    seen = set()
    out = []
    for idx, item in enumerate(items):
        chunk_id = item.get('chunk_id')
        if chunk_id is None:
            key = (item.get(key_name), hash(item.get('excerpt', '')), idx)
        else:
            key = (item.get(key_name), chunk_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def normalize():
    """Main normalization. Returns dict with counts.

    Keeps the ``weight`` field from extraction if present.
    """
    data = load_json(KB_CANDIDATES, default={})
    out = {}
    out['themes'] = dedupe([x for x in data.get('themes', []) if keep(x)], 'theme_name')
    out['principles'] = dedupe([x for x in data.get('principles', []) if keep(x)], 'principle_name')
    out['patterns'] = dedupe([x for x in data.get('patterns', []) if keep(x)], 'pattern_name')
    save_json(KB_CANDIDATES_NORM, out)
    return {k: len(v) for k, v in out.items()}
