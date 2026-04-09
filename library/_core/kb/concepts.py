#!/usr/bin/env python3
"""Import book-specific concepts (cases / intervention examples) into the KB."""
from library.config import (
    DB_PATH, BEYOND_ORDER_CONCEPTS, MAPS_OF_MEANING_CONCEPTS, TWELVE_RULES_CONCEPTS,
)
from library.db import connect, ensure_case
from library.utils import load_json


def _ensure_intervention_example(cur, title, summary):
    row = cur.execute('SELECT id FROM intervention_examples WHERE example_name = ?', (title,)).fetchone()
    if row:
        return row[0]
    cur.execute('INSERT INTO intervention_examples (example_name, description) VALUES (?, ?)', (title, summary))
    return cur.lastrowid


def import_beyond_order():
    """Import Beyond Order concepts. Returns counts dict."""
    data = load_json(BEYOND_ORDER_CONCEPTS, default=[])
    with connect() as conn:
        cur = conn.cursor()
        imported = {'cases': 0, 'intervention_examples': 0}
        for item in data:
            title = item['name']
            summary = item['summary']
            if item['type'] == 'frame':
                ensure_case(cur, title, summary, intervention_style='manual-beyond-order', risk_note='manual concept harvest')
                imported['cases'] += 1
            else:
                _ensure_intervention_example(cur, title, summary)
                imported['intervention_examples'] += 1
    return imported


def import_maps_of_meaning():
    """Import Maps of Meaning concepts. Returns counts dict."""
    data = load_json(MAPS_OF_MEANING_CONCEPTS, default=[])
    with connect() as conn:
        cur = conn.cursor()
        imported = 0
        for item in data:
            ensure_case(cur, item['name'], item['summary'], intervention_style='manual-maps-of-meaning', risk_note='manual concept harvest')
            imported += 1
    return {'maps_of_meaning_cases_imported': imported}


def import_twelve_rules():
    """Import 12 Rules concepts. Returns counts dict."""
    data = load_json(TWELVE_RULES_CONCEPTS, default=[])
    with connect() as conn:
        cur = conn.cursor()
        imported = 0
        for item in data:
            ensure_case(cur, item['name'], item['summary'], intervention_style='manual-twelve-rules', risk_note='manual concept harvest')
            imported += 1
    return {'twelve_rules_cases_imported': imported}
