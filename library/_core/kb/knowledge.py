#!/usr/bin/env python3
"""Structured knowledge and canonical concept importers."""
from __future__ import annotations

import logging
import re

from library.config import ARTICLE_KNOWLEDGE, CANONICAL_CONCEPTS
from library.db import connect
from library.utils import load_json, slugify

log = logging.getLogger('jordan')

MANUAL_KNOWLEDGE_NOTE = 'manual structured knowledge'
AUTO_CHAPTER_NOTE = 'auto chapter harvest'
MANUAL_CONCEPT_NOTE = 'manual canonical concept seed'

_NOISE_SECTIONS = (
    'содержание', 'оглавление', 'примечан', 'об авторе',
    'благодарност', 'copyright', 'table of contents',
    'index', 'isbn', 'ббк', 'предисловие',
)


def _normalize_text(text: str, max_len: int = 320) -> str:
    text = re.sub(r'\s+', ' ', (text or '')).strip().strip(' "\'«»')
    if len(text) <= max_len:
        return text
    cut = text[:max_len].rsplit(' ', 1)[0].rstrip(' ,;:')
    return (cut or text[:max_len]).rstrip(' ,;:') + '...'


def _normalize_section_title(title: str) -> str:
    title = re.sub(r'\s+', ' ', (title or '')).strip(' .:-—–')
    tokens = title.split()
    merged: list[str] = []
    buffer = ''
    for token in tokens:
        if len(token) == 1 and token.isalpha():
            buffer += token
            continue
        if buffer:
            merged.append(buffer)
            buffer = ''
        merged.append(token)
    if buffer:
        merged.append(buffer)
    return ' '.join(merged).strip(' .:-—–')


def _section_is_noise(title: str) -> bool:
    lower = title.lower()
    if not lower:
        return True
    if lower.startswith('file:') or '.xhtml' in lower:
        return True
    if re.fullmatch(r'[a-z\s]+', lower) and 'index' in lower:
        return True
    if re.fullmatch(r'abcdefghijklmnopqrstuvwxyz', lower.replace(' ', '')):
        return True
    if any(stop in lower for stop in _NOISE_SECTIONS):
        return True
    if re.fullmatch(r'(правило|rule)\s+\d+', lower):
        return False
    if len(lower) < 4:
        return True
    return False


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r'(?<=[.!?])\s+', re.sub(r'\s+', ' ', text).strip())
    return [p.strip(' "\'«»') for p in parts if p.strip()]


def _summary_from_texts(texts: list[str], max_len: int = 360) -> str:
    merged = ' '.join(
        re.sub(r'\s+', ' ', (text or '')).strip()
        for text in texts
        if text and text.strip()
    ).strip()
    if not merged:
        return ''
    sentences = _split_sentences(merged)
    picked: list[str] = []
    for sentence in sentences:
        if sentence.isupper() and len(sentence) > 40:
            continue
        picked.append(sentence)
        if len(' '.join(picked)) >= 220:
            break
        if len(picked) >= 2:
            break
    return _normalize_text(' '.join(picked) or merged, max_len=max_len)


def _section_taxonomy(cur, doc_id: int, section_title: str) -> tuple[str | None, str | None, str | None]:
    theme = cur.execute(
        '''
        SELECT t.theme_name, COUNT(*) AS hits
        FROM theme_evidence e
        JOIN themes t ON t.id = e.theme_id
        JOIN document_chunks dc ON dc.id = e.chunk_id
        JOIN documents d ON d.id = dc.document_id
        WHERE dc.document_id = ?
          AND dc.revision_id = d.active_revision_id
          AND dc.section_title = ?
        GROUP BY t.theme_name
        ORDER BY hits DESC, t.theme_name ASC
        LIMIT 1
        ''',
        (doc_id, section_title),
    ).fetchone()
    principle = cur.execute(
        '''
        SELECT p.principle_name, COUNT(*) AS hits
        FROM principle_evidence e
        JOIN principles p ON p.id = e.principle_id
        JOIN document_chunks dc ON dc.id = e.chunk_id
        JOIN documents d ON d.id = dc.document_id
        WHERE dc.document_id = ?
          AND dc.revision_id = d.active_revision_id
          AND dc.section_title = ?
        GROUP BY p.principle_name
        ORDER BY hits DESC, p.principle_name ASC
        LIMIT 1
        ''',
        (doc_id, section_title),
    ).fetchone()
    pattern = cur.execute(
        '''
        SELECT p.pattern_name, COUNT(*) AS hits
        FROM pattern_evidence e
        JOIN patterns p ON p.id = e.pattern_id
        JOIN document_chunks dc ON dc.id = e.chunk_id
        JOIN documents d ON d.id = dc.document_id
        WHERE dc.document_id = ?
          AND dc.revision_id = d.active_revision_id
          AND dc.section_title = ?
        GROUP BY p.pattern_name
        ORDER BY hits DESC, p.pattern_name ASC
        LIMIT 1
        ''',
        (doc_id, section_title),
    ).fetchone()
    return (
        theme[0] if theme else None,
        principle[0] if principle else None,
        pattern[0] if pattern else None,
    )


def _infer_canonical_slug(text: str, theme_name: str | None,
                          principle_name: str | None,
                          pattern_name: str | None) -> str | None:
    lower = (text or '').lower()
    if any(x in lower for x in ('vision', 'виден', 'aim', 'цель', 'направлен')):
        return 'chosen-aim-organizes-life'
    if any(x in lower for x in ('truth', 'правд', 'narrat', 'lie', 'лг')):
        return 'truthful-speech-orders-chaos'
    if any(x in lower for x in ('комнат', 'local order', 'поряд', 'structure')):
        return 'local-order-precedes-grandiosity'
    if any(x in lower for x in ('fear', 'страх', 'catalyst')):
        return 'fear-reveals-value'
    if any(x in lower for x in ('resent', 'обид', 'гореч', 'bitterness')):
        return 'resentment-is-self-betrayal'
    if any(x in lower for x in ('relationship', 'offer', 'recipro', 'отношен')):
        return 'reciprocal-offer-stabilizes-relationship'
    if any(x in lower for x in ('discipline', 'desire', 'schedule', 'game', 'распис')):
        return 'desire-needs-discipline'
    if any(x in lower for x in ('trag', 'страдан', 'faith', 'suffering')):
        return 'voluntary-confrontation-with-tragedy'
    if principle_name == 'tell-the-truth-or-at-least-dont-lie':
        return 'truthful-speech-orders-chaos'
    if principle_name == 'clean-up-what-is-in-front-of-you':
        return 'local-order-precedes-grandiosity'
    if principle_name == 'take-responsibility-before-blame':
        return 'responsibility-before-blame'
    if pattern_name == 'aimlessness' or theme_name == 'meaning':
        return 'chosen-aim-organizes-life'
    if pattern_name == 'resentment-loop' or theme_name == 'resentment':
        return 'resentment-is-self-betrayal'
    if theme_name == 'suffering':
        return 'voluntary-confrontation-with-tragedy'
    return None


def _canonical_id_map(cur) -> dict[str, int]:
    return {
        slug: concept_id
        for concept_id, slug in cur.execute(
            'SELECT id, concept_slug FROM canonical_concepts'
        ).fetchall()
    }


def _link_concept_source(cur, concept_id: int | None, document_id: int | None,
                         support_type: str, support_ref: str,
                         note: str) -> None:
    if not concept_id or not document_id:
        return
    cur.execute(
        'INSERT OR REPLACE INTO canonical_concept_sources '
        '(concept_id, document_id, support_type, support_ref, note) '
        'VALUES (?, ?, ?, ?, ?)',
        (concept_id, document_id, support_type, support_ref or '', note),
    )


def _upsert_named_row(cur, table: str, unique_col: str, values: dict) -> None:
    cols = list(values.keys())
    placeholders = ', '.join('?' for _ in cols)
    updates = ', '.join(
        f'{col} = excluded.{col}'
        for col in cols
        if col != unique_col
    )
    cur.execute(
        f'INSERT INTO {table} ({", ".join(cols)}) '
        f'VALUES ({placeholders}) '
        f'ON CONFLICT({unique_col}) DO UPDATE SET {updates}',
        tuple(values[col] for col in cols),
    )


def import_canonical_concepts() -> dict:
    data = load_json(CANONICAL_CONCEPTS, default=[])
    if not isinstance(data, list):
        return {'canonical_concepts': 0, 'aliases': 0, 'sources': 0, 'skipped': 1}

    with connect() as conn:
        cur = conn.cursor()
        cur.execute('DELETE FROM canonical_concept_aliases')
        cur.execute(
            'DELETE FROM canonical_concept_sources WHERE note = ?',
            (MANUAL_CONCEPT_NOTE,),
        )

        concepts = 0
        aliases = 0
        sources = 0
        skipped = 0
        for item in data:
            name = (item.get('name') or '').strip()
            slug = (item.get('slug') or slugify(name)).strip()
            if not name or not slug:
                skipped += 1
                continue
            _upsert_named_row(cur, 'canonical_concepts', 'concept_slug', {
                'concept_slug': slug,
                'concept_name': name,
                'description': _normalize_text(item.get('description') or '', 420),
                'theme_name': item.get('theme_name'),
                'principle_name': item.get('principle_name'),
                'pattern_name': item.get('pattern_name'),
                'priority': int(item.get('priority') or 0),
            })
            concept_id = cur.execute(
                'SELECT id FROM canonical_concepts WHERE concept_slug = ?',
                (slug,),
            ).fetchone()[0]
            concepts += 1

            for alias in item.get('aliases') or []:
                alias_text = _normalize_text(alias, 180)
                if not alias_text:
                    continue
                cur.execute(
                    'INSERT OR IGNORE INTO canonical_concept_aliases '
                    '(concept_id, alias_text) VALUES (?, ?)',
                    (concept_id, alias_text),
                )
                aliases += 1

            for document_id in item.get('document_ids') or []:
                if not isinstance(document_id, int):
                    continue
                _link_concept_source(
                    cur, concept_id, document_id,
                    'manual-doc-link', name, MANUAL_CONCEPT_NOTE,
                )
                sources += 1

    return {
        'canonical_concepts': concepts,
        'aliases': aliases,
        'sources': sources,
        'skipped': skipped,
    }


def import_structured_knowledge() -> dict:
    data = load_json(ARTICLE_KNOWLEDGE, default=[])
    if not isinstance(data, list):
        return {
            'definitions': 0,
            'claims': 0,
            'practices': 0,
            'objections': 0,
            'skipped': 1,
        }

    covered_doc_ids = sorted({
        int(item.get('source_document_id'))
        for item in data
        if item.get('source_document_id') is not None
    })

    with connect() as conn:
        cur = conn.cursor()
        if covered_doc_ids:
            placeholders = ','.join('?' for _ in covered_doc_ids)
            params = (MANUAL_KNOWLEDGE_NOTE, *covered_doc_ids)
            for table in ('definitions', 'claims', 'practices', 'objections'):
                cur.execute(
                    f'DELETE FROM {table} WHERE note = ? '
                    f'AND source_document_id IN ({placeholders})',
                    params,
                )
            cur.execute(
                f'DELETE FROM canonical_concept_sources '
                f'WHERE note = ? AND document_id IN ({placeholders}) '
                f'AND support_type IN (?, ?, ?, ?)',
                (
                    MANUAL_KNOWLEDGE_NOTE,
                    *covered_doc_ids,
                    'definition', 'claim', 'practice', 'objection',
                ),
            )

        concept_ids = _canonical_id_map(cur)
        imported = {
            'definitions': 0,
            'claims': 0,
            'practices': 0,
            'objections': 0,
            'skipped': 0,
        }

        for item in data:
            item_type = (item.get('type') or '').strip()
            name = _normalize_text(item.get('name') or '', 220)
            summary = _normalize_text(item.get('summary') or '', 420)
            if not item_type or not name or not summary:
                imported['skipped'] += 1
                continue

            canonical_slug = item.get('canonical_concept_slug')
            concept_id = concept_ids.get(canonical_slug)
            base = {
                'theme_name': item.get('theme_name'),
                'principle_name': item.get('principle_name'),
                'pattern_name': item.get('pattern_name'),
                'source_document_id': item.get('source_document_id'),
                'canonical_concept_id': concept_id,
                'note': MANUAL_KNOWLEDGE_NOTE,
            }
            if item_type == 'definition':
                _upsert_named_row(cur, 'definitions', 'term_name', {
                    'term_name': name,
                    'summary': summary,
                    **base,
                })
                imported['definitions'] += 1
            elif item_type == 'claim':
                _upsert_named_row(cur, 'claims', 'claim_text', {
                    'claim_text': name,
                    'summary': summary,
                    'claim_kind': item.get('claim_kind') or 'manual-claim',
                    **base,
                })
                imported['claims'] += 1
            elif item_type == 'practice':
                _upsert_named_row(cur, 'practices', 'practice_name', {
                    'practice_name': name,
                    'summary': summary,
                    'difficulty': item.get('difficulty') or 'medium',
                    'time_horizon': item.get('time_horizon') or 'days-to-weeks',
                    **base,
                })
                imported['practices'] += 1
            elif item_type == 'objection':
                _upsert_named_row(cur, 'objections', 'objection_name', {
                    'objection_name': name,
                    'summary': summary,
                    'response': _normalize_text(item.get('response') or '', 420),
                    **base,
                })
                imported['objections'] += 1
            else:
                imported['skipped'] += 1
                continue

            _link_concept_source(
                cur,
                concept_id,
                item.get('source_document_id'),
                item_type,
                name,
                MANUAL_KNOWLEDGE_NOTE,
            )

    return imported


def build_chapter_summaries() -> dict:
    with connect() as conn:
        cur = conn.cursor()
        concept_ids = _canonical_id_map(cur)
        cur.execute('DELETE FROM chapter_summaries WHERE note = ?', (AUTO_CHAPTER_NOTE,))
        cur.execute(
            'DELETE FROM canonical_concept_sources '
            'WHERE note = ? AND support_type = ?',
            (AUTO_CHAPTER_NOTE, 'chapter-summary'),
        )

        section_rows = cur.execute(
            '''
            SELECT d.id, d.source_pdf, dc.section_title, COUNT(*) AS chunk_count,
                   MIN(dc.chunk_index) AS first_chunk_index
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE dc.revision_id = d.active_revision_id
              AND dc.section_title IS NOT NULL
              AND TRIM(dc.section_title) <> ''
            GROUP BY d.id, d.source_pdf, dc.section_title
            ORDER BY d.id ASC, first_chunk_index ASC
            '''
        ).fetchall()

        imported = 0
        skipped = 0
        for document_id, source_pdf, raw_title, chunk_count, _first_idx in section_rows:
            title = _normalize_section_title(raw_title or '')
            if not title or _section_is_noise(title):
                skipped += 1
                continue
            if source_pdf.startswith('books/') and int(chunk_count or 0) < 2:
                skipped += 1
                continue

            texts = [
                row[0]
                for row in cur.execute(
                    '''
                    SELECT dc.content
                    FROM document_chunks dc
                    JOIN documents d ON d.id = dc.document_id
                    WHERE dc.document_id = ?
                      AND dc.revision_id = d.active_revision_id
                      AND dc.section_title = ?
                    ORDER BY dc.chunk_index ASC
                    LIMIT 2
                    ''',
                    (document_id, raw_title),
                ).fetchall()
            ]
            summary = _summary_from_texts(texts)
            if not summary:
                skipped += 1
                continue
            summary_lower = summary.lower()
            if (
                summary_lower.startswith('# file:')
                or 'table of contents' in summary_lower
                or 'index the page numbers' in summary_lower
            ):
                skipped += 1
                continue

            theme_name, principle_name, pattern_name = _section_taxonomy(
                cur, document_id, raw_title,
            )
            canonical_slug = _infer_canonical_slug(
                f'{title} {summary}',
                theme_name,
                principle_name,
                pattern_name,
            )
            concept_id = concept_ids.get(canonical_slug)
            cur.execute(
                'INSERT INTO chapter_summaries '
                '(document_id, section_title, summary, theme_name, principle_name, '
                'pattern_name, canonical_concept_id, note) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?) '
                'ON CONFLICT(document_id, section_title) DO UPDATE SET '
                'summary = excluded.summary, '
                'theme_name = excluded.theme_name, '
                'principle_name = excluded.principle_name, '
                'pattern_name = excluded.pattern_name, '
                'canonical_concept_id = excluded.canonical_concept_id, '
                'note = excluded.note',
                (
                    document_id,
                    title,
                    summary,
                    theme_name,
                    principle_name,
                    pattern_name,
                    concept_id,
                    AUTO_CHAPTER_NOTE,
                ),
            )
            _link_concept_source(
                cur, concept_id, document_id,
                'chapter-summary', title, AUTO_CHAPTER_NOTE,
            )
            imported += 1

    return {'chapter_summaries': imported, 'skipped': skipped}
