#!/usr/bin/env python3
"""Quote pipeline: extract, normalize, and load quotes into the knowledge base."""
import re

from library.config import (
    DB_PATH, QUOTES_CANDIDATES, QUOTES_NORMALIZED,
    MANUAL_QUOTES, MANUAL_QUOTES_BEYOND, MANUAL_QUOTES_MAPS,
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

BAD_SNIPPETS = [
    'правило 9',
    'правило 10',
    'оглавление',
    'table of contents',
    'copyright',
    'isbn',
    'random house',
    'toronto:',
    'london:',
    'footnote',
    'see also',
    'удк',
    'ббк',
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
    text = _clean(item.get('quote_text', ''))
    lowered = text.lower()
    if len(text) < 60:
        return False
    if any(b in lowered for b in BAD_SNIPPETS):
        return False
    if 'не позволяйте детям' in lowered and 'наведите идеальный порядок у себя дома' in lowered:
        return False
    if sum(ch.isdigit() for ch in text) > 18:
        return False
    if sum(1 for ch in text if ch.isupper()) > max(25, len(text) * 0.35):
        return False
    if text.count(':') >= 3:
        return False
    if text.count('.') <= 0 and len(text) > 180:
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

def extract_quotes():
    """Extract quote candidates from document chunks. Returns result dict."""
    with connect() as conn:
        cur = conn.cursor()
        rows = cur.execute('SELECT id, document_id, content FROM document_chunks').fetchall()
    out = []
    for chunk_id, document_id, content in rows:
        text = re.sub(r'\s+', ' ', content).strip()
        lowered = text.lower()
        for pat in QUOTE_PATTERNS:
            m = re.search(pat, lowered)
            if m:
                start = max(0, m.start() - 80)
                end = min(len(text), m.end() + 220)
                snippet = text[start:end].strip()
                out.append({
                    'document_id': document_id,
                    'chunk_id': chunk_id,
                    'quote_text': snippet,
                    'note': f'matched pattern: {pat}',
                })
                break
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
        key = quote[:160].lower()
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
    """Load normalized + manual quotes into the DB. Returns result dict."""
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

    with connect() as conn:
        cur = conn.cursor()
        cur.execute('DELETE FROM quotes')
        for item in data:
            cur.execute(
                'INSERT INTO quotes (document_id, chunk_id, quote_text, note, quote_type, theme_name, principle_name, pattern_name) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    item['document_id'],
                    item['chunk_id'],
                    item['quote_text'],
                    item['note'],
                    item.get('quote_type'),
                    item.get('theme_name'),
                    item.get('principle_name'),
                    item.get('pattern_name'),
                ),
            )
        count = cur.execute('SELECT COUNT(*) FROM quotes').fetchone()[0]
    return {'quotes': count}
