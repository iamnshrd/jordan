#!/usr/bin/env python3
"""Quote pipeline: extract, normalize, and load quotes into the knowledge base."""
import hashlib
import re

from library.config import (
    QUOTES_CANDIDATES, QUOTES_NORMALIZED,
    MANUAL_QUOTES, MANUAL_QUOTES_BEYOND, MANUAL_QUOTES_MAPS,
    COMMON_STOP_SNIPPETS,
)
from library.db import connect
from library.utils import load_json, save_json

# ── extraction patterns ──────────────────────────────────────────────────────

QUOTE_PATTERNS = [
    r'говори(?:те)? правд[^.]{0,220}',
    r'tell the truth[^.]{0,220}',
    r'сравнивай(?:те)? себя[^.]{0,220}',
    r'compare yourself[^.]{0,220}',
    r'обращайтесь с собой[^.]{0,220}',
    r'treat yourself like[^.]{0,220}',
    r'убер(?:и|ите) свою комнат[^.]{0,220}',
    r'clean your room[^.]{0,220}',
    r'наведите идеальный порядок у себя дома[^.]{0,220}',
    r'perfect order in your house[^.]{0,220}',
    r'не позволяйте детям[^.]{0,220}',
    r'do not let your children[^.]{0,220}',
    r'предполага(?:й|йте), что человек[^.]{0,220}',
    r'assume that the person[^.]{0,220}',
    r'стыд[^.]{0,220}',
    r'позор[^.]{0,220}',
    r'shame[^.]{0,220}',
    r'resentment[^.]{0,220}',
    r'обида[^.]{0,220}',
]

# ── normalization filters ────────────────────────────────────────────────────

BAD_SNIPPETS = COMMON_STOP_SNIPPETS + [
    'правило 9',
    'правило 10',
    'toronto:',
    'london:',
]


def _clean(text):
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\.{2,}', '.', text)
    return text


def _classify_quote(text):
    lower = text.lower()
    if 'говорите правду' in lower or 'не лгите' in lower or 'tell the truth' in lower or "don't lie" in lower:
        return ('principle-quote', 'truth', 'tell-the-truth-or-at-least-dont-lie', 'avoidance-loop')
    if 'сравнивайте себя' in lower or 'compare yourself' in lower:
        return ('principle-quote', 'meaning', None, 'aimlessness')
    if 'обращайтесь с собой' in lower or 'treat yourself like someone' in lower:
        return ('principle-quote', 'responsibility', 'take-responsibility-before-blame', None)
    if 'не позволяйте детям' in lower or 'do not let your children' in lower:
        return ('relationship-quote', 'responsibility', None, None)
    if 'убери' in lower or 'комнат' in lower or 'порядок у себя дома' in lower or 'наведите идеальный порядок у себя дома' in lower or 'clean your room' in lower or 'perfect order in your house' in lower:
        return ('discipline-quote', 'order-and-chaos', 'clean-up-what-is-in-front-of-you', 'avoidance-loop')
    if 'стыд' in lower or 'позор' in lower or 'отвращение к себе' in lower or 'shame' in lower:
        return ('shame-quote', 'suffering', None, 'avoidance-loop')
    if 'обида' in lower or 'горечь' in lower or 'resentment' in lower:
        return ('resentment-quote', 'resentment', None, 'resentment-loop')
    return ('general-quote', None, None, None)


def _keep_quote(item):
    from library.utils import get_threshold
    text = _clean(item.get('quote_text', ''))
    lowered = text.lower()
    if len(text) < get_threshold('quote_min_length', 60):
        return False
    if any(b in lowered for b in BAD_SNIPPETS):
        return False
    if 'не позволяйте детям' in lowered and 'наведите идеальный порядок у себя дома' in lowered:
        return False
    if sum(ch.isdigit() for ch in text) > get_threshold('quote_max_digit_count', 18):
        return False
    max_upper_abs = get_threshold('quote_max_uppercase_abs', 25)
    max_upper_pct = get_threshold('quote_max_uppercase_pct', 0.35)
    if sum(1 for ch in text if ch.isupper()) > max(max_upper_abs, len(text) * max_upper_pct):
        return False
    if text.count(':') >= get_threshold('quote_max_colons', 3):
        return False
    min_periods_len = get_threshold('quote_min_periods_for_long', 180)
    if text.count('.') <= 0 and len(text) > min_periods_len:
        return False
    if any(x in lowered for x in ['rule i', 'rule ii', 'rule iii', 'rule iv', 'rule v', 'rule vi', 'rule vii', 'rule viii', 'rule ix', 'rule x', 'rule xi', 'rule xii']):
        return False
    if re.search(r'\b\d{2,4}\b(?:\s+\b\d{2,4}\b){3,}', lowered):
        return False
    if re.search(r'\b[A-ZА-ЯЁ]{4,}\b(?:\s+\b[A-ZА-ЯЁ]{4,}\b){3,}', text):
        return False
    if not any(x in lowered for x in ['правд', 'tell the truth', 'сравнива', 'compare yourself', 'обращайтесь', 'treat yourself like', 'убери', 'clean your room', 'предполаг', 'assume that the person', 'не позволяйте', 'do not let your children', 'порядок у себя дома', 'perfect order in your house', 'стыд', 'позор', 'shame', 'обида', 'горечь', 'resentment']):
        return False
    return True


# ── public pipeline functions ────────────────────────────────────────────────

def _spans_overlap(a_start, a_end, b_start, b_end, threshold=0.5):
    """Return True if two spans overlap by more than *threshold* of the smaller."""
    overlap = max(0, min(a_end, b_end) - max(a_start, b_start))
    smaller = min(a_end - a_start, b_end - b_start) or 1
    return overlap / smaller > threshold


def extract_quotes():
    """Extract quote candidates from document chunks. Returns result dict."""
    out = []
    batch_size = 500
    offset = 0
    with connect() as conn:
        while True:
            rows = conn.cursor().execute(
                'SELECT dc.id, dc.document_id, dc.content '
                'FROM document_chunks dc '
                'JOIN documents d ON d.id = dc.document_id '
                'WHERE dc.revision_id = d.active_revision_id '
                'ORDER BY dc.id LIMIT ? OFFSET ?',
                (batch_size, offset),
            ).fetchall()
            if not rows:
                break
            offset += len(rows)
            for chunk_id, document_id, content in rows:
                if not content:
                    continue
                text = re.sub(r'\s+', ' ', content).strip()
                used_spans: list[tuple[int, int]] = []
                for priority, pat in enumerate(QUOTE_PATTERNS):
                    for m in re.finditer(pat, text, re.IGNORECASE):
                        start = max(0, m.start() - 80)
                        end = min(len(text), m.end() + 220)
                        if any(_spans_overlap(start, end, s, e) for s, e in used_spans):
                            continue
                        snippet = text[start:end].strip()
                        used_spans.append((start, end))
                        out.append({
                            'document_id': document_id,
                            'chunk_id': chunk_id,
                            'quote_text': snippet,
                            'note': f'matched pattern: {pat}',
                            'pattern_priority': priority,
                        })
    save_json(QUOTES_CANDIDATES, out)
    return {'quote_candidates': len(out)}


def normalize_quotes():
    """Normalize and classify quote candidates. Returns result dict."""
    data = load_json(QUOTES_CANDIDATES, default=[])
    out = []
    seen = set()
    for item in data:
        if not _keep_quote(item):
            continue
        quote = _clean(item['quote_text'])
        key = hashlib.sha256(quote.lower().encode()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        qtype, theme, principle, pattern = _classify_quote(quote)
        item['quote_text'] = quote
        item['quote_type'] = qtype
        item['theme_name'] = theme
        item['principle_name'] = principle
        item['pattern_name'] = pattern
        out.append(item)
    save_json(QUOTES_NORMALIZED, out)
    return {'quotes_normalized': len(out)}


def load_quotes():
    """Load normalized + manual quotes into the DB atomically. Returns result dict."""
    import logging
    _log = logging.getLogger('jordan')

    data = load_json(QUOTES_NORMALIZED, default=[])
    manual = load_json(MANUAL_QUOTES, default=[])
    if manual:
        data.extend(manual)
    manual_beyond = load_json(MANUAL_QUOTES_BEYOND, default=[])
    if manual_beyond:
        data.extend(manual_beyond)
    manual_maps = load_json(MANUAL_QUOTES_MAPS, default=[])
    if manual_maps:
        data.extend(manual_maps)

    required_keys = ('document_id', 'chunk_id', 'quote_text', 'note')
    valid: list[dict] = []
    skipped = 0
    for item in data:
        if all(k in item for k in required_keys):
            valid.append(item)
        else:
            skipped += 1
    if skipped:
        _log.warning('load_quotes: skipped %d items with missing keys', skipped)

    with connect() as conn:
        cur = conn.cursor()
        cur.execute('BEGIN IMMEDIATE')
        try:
            cur.execute('DELETE FROM quotes')
            fk_skipped = 0
            for item in valid:
                doc_id = item['document_id']
                chunk_id = item['chunk_id']
                exists = cur.execute(
                    'SELECT 1 FROM document_chunks dc '
                    'JOIN documents d ON d.id = dc.document_id '
                    'WHERE dc.id = ? AND dc.document_id = ? '
                    'AND dc.revision_id = d.active_revision_id',
                    (chunk_id, doc_id),
                ).fetchone()
                if not exists:
                    fk_skipped += 1
                    continue
                cur.execute(
                    'INSERT INTO quotes (document_id, chunk_id, quote_text, note, quote_type, theme_name, principle_name, pattern_name) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (
                        doc_id,
                        chunk_id,
                        item['quote_text'],
                        item['note'],
                        item.get('quote_type'),
                        item.get('theme_name'),
                        item.get('principle_name'),
                        item.get('pattern_name'),
                    ),
                )
            conn.commit()
            if fk_skipped:
                _log.warning('load_quotes: skipped %d items with invalid document_id/chunk_id', fk_skipped)
        except Exception:
            conn.rollback()
            raise
        count = cur.execute('SELECT COUNT(*) FROM quotes').fetchone()[0]
    return {'quotes': count}
