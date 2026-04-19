#!/usr/bin/env python3
"""Import concepts (manual + harvested) into the KB."""
import logging
import re

from library.config import (
    ARTICLE_CONCEPTS, BEYOND_ORDER_CONCEPTS, MAPS_OF_MEANING_CONCEPTS,
    TWELVE_RULES_CONCEPTS,
)
from library.db import connect, ensure_case
from library.utils import load_json

log = logging.getLogger('jordan')


def _ensure_intervention_example(cur, title, summary, item=None):
    row = cur.execute('SELECT id FROM intervention_examples WHERE example_name = ?', (title,)).fetchone()
    if row:
        eid = row[0]
        cur.execute(
            'UPDATE intervention_examples SET description = ? WHERE id = ?',
            (summary, eid),
        )
    else:
        cur.execute('INSERT INTO intervention_examples (example_name, description) VALUES (?, ?)', (title, summary))
        eid = cur.lastrowid
    if item:
        for col in ('theme_name', 'principle_name', 'pattern_name', 'source_document_id'):
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
                    intervention_style=item.get('intervention_style', intervention_style),
                    risk_note=item.get('note', 'manual concept harvest'),
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


_QUOTE_TYPE_RANK = {
    'discipline-quote': 0,
    'principle-quote': 1,
    'relationship-quote': 2,
    'resentment-quote': 3,
    'shame-quote': 4,
    'general-quote': 9,
}


def _short_source_title(source_pdf: str) -> str:
    name = source_pdf.rsplit('/', 1)[-1].rsplit('.', 1)[0]
    name = name.replace('Peterson Academy — ', '')
    name = name.replace('Джордан Питерсон | ', '')
    name = name.replace('Джордан Питерсон — ', '')
    return name.strip()


def _normalize_summary(text: str, max_len: int = 260) -> str:
    text = re.sub(r'\s+', ' ', (text or '')).strip().strip(' "\'«»')
    if len(text) <= max_len:
        return text
    cut = text[:max_len].rsplit(' ', 1)[0].rstrip(' ,;:')
    return (cut or text[:max_len]).rstrip(' ,;:') + '...'


def _case_title(source_pdf: str, theme: str, quote_text: str) -> str:
    title_map = {
        'meaning': 'selected aim',
        'responsibility': 'assumed responsibility',
        'order-and-chaos': 'structure before drift',
        'truth': 'truth before avoidance',
        'resentment': 'resentment named directly',
        'suffering': 'suffering faced voluntarily',
    }
    return f'{_short_source_title(source_pdf)} — {title_map.get(theme or "", "core concept")}'


def _example_title(source_pdf: str, principle: str, pattern: str) -> str:
    focus = principle or pattern or 'practical move'
    return f'{_short_source_title(source_pdf)} — {focus}'


def _intervention_style(theme: str, principle: str) -> str:
    if principle == 'clean-up-what-is-in-front-of-you' or theme == 'order-and-chaos':
        return 'practical-ordering'
    if theme == 'meaning':
        return 'symbolic-reframing'
    return 'responsibility-first'


def _pick_case_quote(quotes: list[dict]) -> dict | None:
    ranked = sorted(
        quotes,
        key=lambda q: (
            _QUOTE_TYPE_RANK.get(q.get('quote_type') or '', 99),
            -len(q.get('quote_text') or ''),
        ),
    )
    return ranked[0] if ranked else None


def _pick_example_quote(quotes: list[dict]) -> dict | None:
    def practical_score(item: dict) -> tuple[int, int]:
        text = (item.get('quote_text') or '').lower()
        score = 0
        if any(x in text for x in [
            'you need to', 'you should', 'you have to', 'plan', 'write',
            'set', 'aim', 'tell the truth', 'нужно', 'надо', 'следует',
            'сделай', 'определи', 'запиши', 'план', 'цель', 'распис',
        ]):
            score += 3
        score += max(0, 5 - _QUOTE_TYPE_RANK.get(item.get('quote_type') or '', 9))
        return (score, len(item.get('quote_text') or ''))

    ranked = sorted(quotes, key=practical_score, reverse=True)
    return ranked[0] if ranked else None


def _delete_article_rows(cur, doc_ids: set[int]) -> None:
    """Delete previously imported article rows for the provided doc ids."""
    if not doc_ids:
        return
    placeholders = ','.join('?' for _ in doc_ids)
    cur.execute(
        f'DELETE FROM cases WHERE source_document_id IN ({placeholders})',
        tuple(sorted(doc_ids)),
    )
    cur.execute(
        f'DELETE FROM intervention_examples WHERE source_document_id IN ({placeholders})',
        tuple(sorted(doc_ids)),
    )


def _import_article_concepts_manual():
    """Import manually curated concepts for article/transcript docs."""
    data = load_json(ARTICLE_CONCEPTS, default=[])
    if not data:
        return {'cases': 0, 'intervention_examples': 0, 'skipped': 0}, set()
    manual_doc_ids = {
        int(item.get('source_document_id'))
        for item in data
        if item.get('source_document_id') is not None
    }
    with connect() as conn:
        cur = conn.cursor()
        _delete_article_rows(cur, manual_doc_ids)
    imported = _import_concepts(data, 'manual-articles')
    return imported, manual_doc_ids


def import_article_concepts():
    """Import article concepts with manual curation first and auto fallback second."""
    manual_imported, manual_doc_ids = _import_article_concepts_manual()

    auto_imported = {'cases': 0, 'intervention_examples': 0, 'skipped': 0}
    with connect() as conn:
        cur = conn.cursor()
        article_docs = cur.execute(
            "SELECT id, source_pdf FROM documents WHERE source_pdf LIKE 'articles/%' ORDER BY id"
        ).fetchall()
        for document_id, source_pdf in article_docs:
            if document_id in manual_doc_ids:
                continue
            top_theme = cur.execute(
                '''
                SELECT t.theme_name, COUNT(*) c
                FROM theme_evidence e
                JOIN themes t ON t.id = e.theme_id
                JOIN document_chunks dc ON dc.id = e.chunk_id
                JOIN documents d ON d.id = dc.document_id
                WHERE d.id = ? AND dc.revision_id = d.active_revision_id
                GROUP BY t.theme_name
                ORDER BY c DESC, t.theme_name ASC
                LIMIT 1
                ''',
                (document_id,),
            ).fetchone()
            top_principle = cur.execute(
                '''
                SELECT p.principle_name, COUNT(*) c
                FROM principle_evidence e
                JOIN principles p ON p.id = e.principle_id
                JOIN document_chunks dc ON dc.id = e.chunk_id
                JOIN documents d ON d.id = dc.document_id
                WHERE d.id = ? AND dc.revision_id = d.active_revision_id
                GROUP BY p.principle_name
                ORDER BY c DESC, p.principle_name ASC
                LIMIT 1
                ''',
                (document_id,),
            ).fetchone()
            top_pattern = cur.execute(
                '''
                SELECT p.pattern_name, COUNT(*) c
                FROM pattern_evidence e
                JOIN patterns p ON p.id = e.pattern_id
                JOIN document_chunks dc ON dc.id = e.chunk_id
                JOIN documents d ON d.id = dc.document_id
                WHERE d.id = ? AND dc.revision_id = d.active_revision_id
                GROUP BY p.pattern_name
                ORDER BY c DESC, p.pattern_name ASC
                LIMIT 1
                ''',
                (document_id,),
            ).fetchone()
            quotes = [
                {
                    'quote_text': row[0],
                    'quote_type': row[1],
                }
                for row in cur.execute(
                    'SELECT quote_text, quote_type FROM quotes WHERE document_id = ? ORDER BY id',
                    (document_id,),
                ).fetchall()
            ]
            if not quotes:
                auto_imported['skipped'] += 1
                continue

            theme_name = top_theme[0] if top_theme else None
            principle_name = top_principle[0] if top_principle else None
            pattern_name = top_pattern[0] if top_pattern else None
            style = _intervention_style(theme_name or '', principle_name or '')

            case_quote = _pick_case_quote(quotes)
            if case_quote:
                case_name = _case_title(source_pdf, theme_name or '', case_quote['quote_text'])
                summary = _normalize_summary(case_quote['quote_text'])
                cur.execute(
                    'INSERT INTO cases (case_name, description, intervention_style, risk_note, theme_name, principle_name, pattern_name, source_document_id) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?) '
                    'ON CONFLICT(case_name) DO UPDATE SET '
                    'description = excluded.description, '
                    'intervention_style = excluded.intervention_style, '
                    'risk_note = excluded.risk_note, '
                    'theme_name = excluded.theme_name, '
                    'principle_name = excluded.principle_name, '
                    'pattern_name = excluded.pattern_name, '
                    'source_document_id = excluded.source_document_id',
                    (
                        case_name,
                        summary,
                        style,
                        'auto article harvest',
                        theme_name,
                        principle_name,
                        pattern_name,
                        document_id,
                    ),
                )
                auto_imported['cases'] += 1

            example_quote = _pick_example_quote(quotes)
            if example_quote:
                _ensure_intervention_example(
                    cur,
                    _example_title(source_pdf, principle_name or '', pattern_name or ''),
                    _normalize_summary(example_quote['quote_text']),
                    {
                        'theme_name': theme_name,
                        'principle_name': principle_name,
                        'pattern_name': pattern_name,
                        'source_document_id': document_id,
                    },
                )
                auto_imported['intervention_examples'] += 1
    return {
        'manual': manual_imported,
        'auto_fallback': auto_imported,
    }
