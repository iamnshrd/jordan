#!/usr/bin/env python3
"""Import book-specific concepts (cases / intervention examples) into the KB."""
import logging

from library.config import (
    BEYOND_ORDER_CONCEPTS, MAPS_OF_MEANING_CONCEPTS, TWELVE_RULES_CONCEPTS,
)
from library.db import connect, ensure_case
from library.utils import load_json

log = logging.getLogger('jordan')


def _ensure_intervention_example(cur, title, summary, item=None):
    row = cur.execute('SELECT id FROM intervention_examples WHERE example_name = ?', (title,)).fetchone()
    if row:
        eid = row[0]
    else:
        cur.execute('INSERT INTO intervention_examples (example_name, description) VALUES (?, ?)', (title, summary))
        eid = cur.lastrowid
    if item:
        for col in ('theme_name', 'principle_name', 'pattern_name'):
            val = item.get(col)
            if val:
                try:
                    cur.execute(
                        f'UPDATE intervention_examples SET {col} = ? WHERE id = ?',
                        (val, eid),
                    )
                except Exception as exc:
                    log.warning('Failed to set %s on intervention_example %d: %s',
                                col, eid, exc)
    return eid


def _update_case_taxonomy(cur, case_id, item):
    """Write theme_name/principle_name/pattern_name/source_document_id onto an existing case row."""
    cur.execute(
        'UPDATE cases SET theme_name=?, principle_name=?, pattern_name=?, source_document_id=? WHERE id=?',
        (
            item.get('theme_name'),
            item.get('principle_name'),
            item.get('pattern_name'),
            item.get('source_document_id'),
            case_id,
        ),
    )


def _import_concepts(data, intervention_style):
    """Shared import logic: create case/example rows and store taxonomy."""
    with connect() as conn:
        cur = conn.cursor()
        imported = {'cases': 0, 'intervention_examples': 0, 'skipped': 0}
        for item in data:
            title = item.get('name')
            summary = item.get('summary')
            if not title or not summary:
                log.warning('Skipping concept with missing name/summary: %s', item)
                imported['skipped'] += 1
                continue
            if item.get('type') in ('frame', None):
                case_id = ensure_case(
                    cur, title, summary,
                    intervention_style=intervention_style,
                    risk_note='manual concept harvest',
                )
                _update_case_taxonomy(cur, case_id, item)
                imported['cases'] += 1
            else:
                _ensure_intervention_example(cur, title, summary, item)
                imported['intervention_examples'] += 1
    return imported


def import_beyond_order():
    """Import Beyond Order concepts. Returns counts dict."""
    data = load_json(BEYOND_ORDER_CONCEPTS, default=[])
    return _import_concepts(data, 'manual-beyond-order')


def import_maps_of_meaning():
    """Import Maps of Meaning concepts. Returns counts dict."""
    data = load_json(MAPS_OF_MEANING_CONCEPTS, default=[])
    return _import_concepts(data, 'manual-maps-of-meaning')


def import_twelve_rules():
    """Import 12 Rules concepts. Returns counts dict."""
    data = load_json(TWELVE_RULES_CONCEPTS, default=[])
    return _import_concepts(data, 'manual-twelve-rules')
