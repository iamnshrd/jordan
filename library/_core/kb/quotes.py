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

FALLBACK_QUOTE_KEYWORDS = [
    'meaning', 'purpose', 'vision', 'goal', 'ideal', 'responsibility',
    'truth', 'lie', 'order', 'chaos', 'discipline', 'schedule', 'plan',
    'relationship', 'resentment', 'gratitude', 'courage', 'children',
    'wife', 'husband', 'marriage', 'married', 'romance', 'partner',
    'love', 'betray', 'boundary', 'boundaries', 'intimacy', 'sexual',
    'sex', 'desire', 'rejection', 'conflict',
    'смысл', 'цель', 'идеал', 'ответствен', 'правд', 'лож', 'поряд',
    'хаос', 'дисциплин', 'расписан', 'план', 'отношен', 'обид',
    'благодар', 'мужеств', 'дет', 'границ', 'добросовест',
    'секс', 'сексуал', 'интим', 'близост', 'желание', 'влечен',
    'отверж', 'измен', 'любов', 'конфликт',
]

FALLBACK_MODAL_PATTERNS = [
    r'\byou (?:need to|should|must|have to|can)\b',
    r"\b(?:do not|don't|try to|plan and work|pick|write|set|aim)\b",
    r'\b(?:нужно|надо|следует|должен|можете|попробуй|сделай|определи)\b',
]

COMPACT_QUOTE_KEYWORDS = [
    'relationship', 'wife', 'husband', 'marriage', 'partner', 'romance',
    'love', 'boundary', 'boundaries', 'resentment', 'betray', 'truth',
    'intimacy', 'sexual', 'sex', 'desire', 'rejection', 'gratitude',
    'humility', 'отношен', 'жена', 'муж', 'границ', 'обид', 'любов',
    'секс', 'сексуал', 'интим', 'желани', 'отверж', 'правд',
]

COMPACT_QUOTE_PATTERNS = FALLBACK_MODAL_PATTERNS + [
    r"\byou don't\b",
    r'\bremember\b',
    r'\bthat means\b',
    r'\bthe goal should be\b',
]


def _clean(text):
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\.{2,}', '.', text)
    return text


def _looks_compact_but_strong_quote(text: str) -> bool:
    """Allow short aphoristic lines when they carry clear Jordan-like force."""
    lower = (text or '').lower()
    keyword_hits = sum(1 for kw in COMPACT_QUOTE_KEYWORDS if kw in lower)
    pattern_hits = sum(
        1 for pat in COMPACT_QUOTE_PATTERNS if re.search(pat, lower)
    )
    if not (40 <= len(text) <= 140):
        return False
    return keyword_hits >= 1 and pattern_hits >= 1


def _has_strong_quote_signals(text: str) -> bool:
    lower = (text or '').lower()
    keyword_hits = sum(1 for kw in COMPACT_QUOTE_KEYWORDS if kw in lower)
    pattern_hits = sum(
        1 for pat in COMPACT_QUOTE_PATTERNS if re.search(pat, lower)
    )
    return keyword_hits + (pattern_hits * 2) >= 3


def _match_norm(text):
    """Normalize text for quote-to-chunk matching."""
    return re.sub(r'\s+', ' ', (text or '').lower()).strip()


def _active_chunk_exists(cur, document_id, chunk_id):
    row = cur.execute(
        'SELECT 1 FROM document_chunks dc '
        'JOIN documents d ON d.id = dc.document_id '
        'WHERE dc.id = ? AND dc.document_id = ? '
        'AND dc.revision_id = d.active_revision_id',
        (chunk_id, document_id),
    ).fetchone()
    return bool(row)


def _resolve_quote_chunk_id(cur, document_id, chunk_id, quote_text):
    """Resolve a valid active chunk id for a quote.

    Manual quote packs currently use ``chunk_id = 0`` as a document-level
    placeholder. Prefer an exact substring anchor, then token overlap, and
    finally fall back to the first active chunk in the source document.
    """
    if chunk_id and _active_chunk_exists(cur, document_id, chunk_id):
        return chunk_id, 'as-is'

    rows = cur.execute(
        'SELECT dc.id, dc.content FROM document_chunks dc '
        'JOIN documents d ON d.id = dc.document_id '
        'WHERE dc.document_id = ? AND dc.revision_id = d.active_revision_id '
        'ORDER BY dc.chunk_index',
        (document_id,),
    ).fetchall()
    if not rows:
        return None, 'no-active-chunks'

    norm_quote = _match_norm(quote_text)
    if norm_quote:
        for row_chunk_id, content in rows:
            if norm_quote in _match_norm(content):
                return row_chunk_id, 'substring-match'

    quote_tokens = {
        token for token in re.findall(r'[\w-]+', norm_quote)
        if len(token) >= 4
    }
    if quote_tokens:
        best_chunk_id = None
        best_score = -1
        for row_chunk_id, content in rows:
            content_tokens = {
                token for token in re.findall(r'[\w-]+', _match_norm(content))
                if len(token) >= 4
            }
            score = len(quote_tokens & content_tokens)
            if score > best_score:
                best_score = score
                best_chunk_id = row_chunk_id
        if best_chunk_id is not None and best_score > 0:
            return best_chunk_id, 'token-overlap'

    return rows[0][0], 'first-active-chunk'


def _classify_quote(text):
    lower = text.lower()
    if 'говорите правду' in lower or 'не лгите' in lower or 'tell the truth' in lower or "don't lie" in lower:
        return ('principle-quote', 'truth', 'tell-the-truth-or-at-least-dont-lie', 'avoidance-loop')
    if ('vision' in lower or 'goal' in lower or 'ideal' in lower or 'aim' in lower
            or 'meaningful' in lower or 'значим' in lower or 'цель' in lower
            or 'идеал' in lower or 'смысл' in lower):
        return ('discipline-quote', 'meaning', 'take-responsibility-before-blame', 'aimlessness')
    if 'сравнивайте себя' in lower or 'compare yourself' in lower:
        return ('principle-quote', 'meaning', None, 'aimlessness')
    if ('responsibility' in lower or 'burden' in lower or 'ответствен' in lower
            or 'обязан' in lower):
        return ('principle-quote', 'responsibility', 'take-responsibility-before-blame', 'avoidance-loop')
    if 'обращайтесь с собой' in lower or 'treat yourself like someone' in lower:
        return ('principle-quote', 'responsibility', 'take-responsibility-before-blame', None)
    if ('schedule' in lower or 'расписан' in lower or 'plan' in lower
            or 'discipline' in lower or 'дисциплин' in lower):
        return ('discipline-quote', 'order-and-chaos', 'clean-up-what-is-in-front-of-you', 'avoidance-loop')
    if 'не позволяйте детям' in lower or 'do not let your children' in lower:
        return ('relationship-quote', 'responsibility', None, None)
    if ('обида' in lower or 'горечь' in lower or 'resentment' in lower
            or 'betray' in lower or 'betrayal' in lower):
        return ('resentment-quote', 'resentment', None, 'resentment-loop')
    if ('relationship' in lower or 'romance' in lower or 'границ' in lower
            or 'children' in lower or 'partner' in lower or 'партнер' in lower
            or 'wife' in lower or 'husband' in lower or 'marriage' in lower
            or 'married' in lower or 'intimacy' in lower
            or 'sexual' in lower or 'sex' in lower or 'desire' in lower
            or 'rejection' in lower or 'boundary' in lower
            or 'love' in lower or 'отношен' in lower or 'секс' in lower
            or 'сексуал' in lower or 'интим' in lower or 'близост' in lower
            or 'желани' in lower or 'отверж' in lower or 'любов' in lower):
        return ('relationship-quote', 'responsibility', 'tell-the-truth-or-at-least-dont-lie', 'resentment-loop')
    if 'убери' in lower or 'комнат' in lower or 'порядок у себя дома' in lower or 'наведите идеальный порядок у себя дома' in lower or 'clean your room' in lower or 'perfect order in your house' in lower:
        return ('discipline-quote', 'order-and-chaos', 'clean-up-what-is-in-front-of-you', 'avoidance-loop')
    if 'стыд' in lower or 'позор' in lower or 'отвращение к себе' in lower or 'shame' in lower:
        return ('shame-quote', 'suffering', None, 'avoidance-loop')
    if 'gratitude' in lower or 'thankful' in lower or 'благодар' in lower:
        return ('shame-quote', 'suffering', 'tell-the-truth-or-at-least-dont-lie', 'avoidance-loop')
    return ('general-quote', None, None, None)


def _keep_quote(item):
    from library.utils import get_threshold
    text = _clean(item.get('quote_text', ''))
    lowered = text.lower()
    if (len(text) < get_threshold('quote_min_length', 60)
            and not _looks_compact_but_strong_quote(text)):
        return False
    if any(b in lowered for b in BAD_SNIPPETS):
        return False
    if lowered.count('правило ') >= 2:
        return False
    if re.search(r'(?:\.\s*){8,}', text):
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
    if (text.count('.') <= 0 and len(text) > min_periods_len
            and not _has_strong_quote_signals(text)):
        return False
    if any(x in lowered for x in ['rule i', 'rule ii', 'rule iii', 'rule iv', 'rule v', 'rule vi', 'rule vii', 'rule viii', 'rule ix', 'rule x', 'rule xi', 'rule xii']):
        return False
    if re.search(r'\b\d{2,4}\b(?:\s+\b\d{2,4}\b){3,}', lowered):
        return False
    if re.search(r'\b[A-ZА-ЯЁ]{4,}\b(?:\s+\b[A-ZА-ЯЁ]{4,}\b){3,}', text):
        return False
    if not any(x in lowered for x in [
        'правд', 'tell the truth', 'сравнива', 'compare yourself',
        'обращайтесь', 'treat yourself like', 'убери', 'clean your room',
        'предполаг', 'assume that the person', 'не позволяйте',
        'do not let your children', 'порядок у себя дома',
        'perfect order in your house', 'стыд', 'позор', 'shame',
        'обида', 'горечь', 'resentment', 'vision', 'goal', 'ideal',
        'meaningful', 'смысл', 'цель', 'идеал', 'ответствен',
        'responsibility', 'burden', 'schedule', 'расписан', 'discipline',
        'дисциплин', 'relationship', 'romance', 'отношен', 'границ',
        'gratitude', 'thankful', 'благодар', 'wife', 'husband',
        'marriage', 'partner', 'love', 'betray', 'boundary',
        'intimacy', 'sexual', 'sex', 'desire', 'rejection',
        'секс', 'сексуал', 'интим', 'близост', 'желани', 'отверж',
        'любов', 'конфликт',
    ]):
        return False
    return True


def _split_candidate_sentences(text):
    parts = re.split(r'(?<=[.!?])\s+', _clean(text))
    return [p.strip(' "\'«»') for p in parts if p.strip()]


def _snippet_around_signal(text: str, max_chars: int = 220) -> str:
    """Trim long transcript-style sentences around the first strong signal."""
    text = _clean(text)
    if len(text) <= max_chars:
        return text

    lower = text.lower()
    matches: list[tuple[int, int]] = []
    for keyword in COMPACT_QUOTE_KEYWORDS + FALLBACK_QUOTE_KEYWORDS:
        pos = lower.find(keyword)
        if pos >= 0:
            matches.append((pos, pos + len(keyword)))
    for pattern in COMPACT_QUOTE_PATTERNS:
        hit = re.search(pattern, lower)
        if hit:
            matches.append((hit.start(), hit.end()))

    if not matches:
        return text

    start, end = min(matches, key=lambda item: item[0])
    window_start = max(0, start - 80)
    window_end = min(len(text), window_start + max_chars)
    if end > window_end:
        window_end = min(len(text), end + 60)
        window_start = max(0, window_end - max_chars)
    snippet = text[window_start:window_end].strip(' "\'')

    if window_start > 0 and ' ' in snippet:
        snippet = snippet.split(' ', 1)[1]
    if window_end < len(text) and ' ' in snippet:
        snippet = snippet.rsplit(' ', 1)[0]
    return snippet.strip(' "\'')


def _fallback_quote_score(sentence):
    lower = sentence.lower()
    score = 0
    for kw in FALLBACK_QUOTE_KEYWORDS:
        if kw in lower:
            score += 2
    for pat in FALLBACK_MODAL_PATTERNS:
        if re.search(pat, lower):
            score += 3
    if 70 <= len(sentence) <= 220:
        score += 2
    if sentence[:1].isupper():
        score += 1
    return score


def _build_fallback_quotes(rows, existing_by_doc, existing_quote_texts,
                           target_per_doc=4):
    """Generate curated fallback quotes for under-covered article/transcript docs."""
    out = []
    existing_hashes = {
        hashlib.sha256((text or '').lower().encode()).hexdigest()
        for text in existing_quote_texts
    }
    docs_needed = {
        document_id for document_id, source_pdf, _chunk_id, _content in rows
        if source_pdf.startswith('articles/')
        and existing_by_doc.get(document_id, 0) < target_per_doc
    }
    candidates_by_doc: dict[int, list[tuple[int, str, int, str]]] = {
        doc_id: [] for doc_id in docs_needed
    }
    for document_id, source_pdf, chunk_id, content in rows:
        if document_id not in docs_needed:
            continue
        for sentence in _split_candidate_sentences(content):
            sentence = _snippet_around_signal(sentence)
            if ((len(sentence) < 60 and not _looks_compact_but_strong_quote(sentence))
                    or len(sentence) > 240):
                continue
            if any(bad in sentence.lower() for bad in BAD_SNIPPETS):
                continue
            score = _fallback_quote_score(sentence)
            if score < 5:
                continue
            candidates_by_doc[document_id].append(
                (score, sentence, chunk_id, source_pdf)
            )

    seen_hashes = set(existing_hashes)
    for document_id in sorted(candidates_by_doc):
        needed = max(0, target_per_doc - existing_by_doc.get(document_id, 0))
        ranked = sorted(
            candidates_by_doc[document_id],
            key=lambda item: (-item[0], item[1]),
        )
        added = 0
        for score, sentence, chunk_id, source_pdf in ranked:
            if added >= needed:
                break
            key = hashlib.sha256(sentence.lower().encode()).hexdigest()
            if key in seen_hashes:
                continue
            seen_hashes.add(key)
            added += 1
            out.append({
                'document_id': document_id,
                'chunk_id': chunk_id,
                'quote_text': sentence,
                'note': f'fallback coverage harvest score={score} source={source_pdf.rsplit("/",1)[-1]}',
                'pattern_priority': 999,
            })
    return out


# ── public pipeline functions ────────────────────────────────────────────────

def _spans_overlap(a_start, a_end, b_start, b_end, threshold=0.5):
    """Return True if two spans overlap by more than *threshold* of the smaller."""
    overlap = max(0, min(a_end, b_end) - max(a_start, b_start))
    smaller = min(a_end - a_start, b_end - b_start) or 1
    return overlap / smaller > threshold


def extract_quotes():
    """Extract quote candidates from document chunks. Returns result dict."""
    out = []
    rows_cache = []
    by_doc = {}
    batch_size = 500
    offset = 0
    with connect() as conn:
        while True:
            rows = conn.cursor().execute(
                'SELECT dc.id, dc.document_id, d.source_pdf, dc.content '
                'FROM document_chunks dc '
                'JOIN documents d ON d.id = dc.document_id '
                'WHERE dc.revision_id = d.active_revision_id '
                'ORDER BY dc.id LIMIT ? OFFSET ?',
                (batch_size, offset),
            ).fetchall()
            if not rows:
                break
            offset += len(rows)
            rows_cache.extend([(document_id, source_pdf, chunk_id, content) for chunk_id, document_id, source_pdf, content in rows])
            for chunk_id, document_id, source_pdf, content in rows:
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
                        snippet = _snippet_around_signal(text[start:end]).strip()
                        used_spans.append((start, end))
                        out.append({
                            'document_id': document_id,
                            'chunk_id': chunk_id,
                            'quote_text': snippet,
                            'note': f'matched pattern: {pat}',
                            'pattern_priority': priority,
                        })
                        by_doc[document_id] = by_doc.get(document_id, 0) + 1
    existing_quote_texts = [item.get('quote_text', '') for item in out]
    out.extend(_build_fallback_quotes(rows_cache, by_doc, existing_quote_texts))
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
            resolved = 0
            for item in valid:
                doc_id = item['document_id']
                chunk_id = item['chunk_id']
                resolved_chunk_id, resolution = _resolve_quote_chunk_id(
                    cur, doc_id, chunk_id, item.get('quote_text', ''),
                )
                if resolved_chunk_id is None:
                    fk_skipped += 1
                    continue
                if resolution != 'as-is':
                    resolved += 1
                cur.execute(
                    'INSERT INTO quotes (document_id, chunk_id, quote_text, note, quote_type, theme_name, principle_name, pattern_name) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (
                        doc_id,
                        resolved_chunk_id,
                        item['quote_text'],
                        f"{item['note']} | chunk-resolution:{resolution}",
                        item.get('quote_type'),
                        item.get('theme_name'),
                        item.get('principle_name'),
                        item.get('pattern_name'),
                    ),
                )
            conn.commit()
            if fk_skipped:
                _log.warning('load_quotes: skipped %d items with invalid document_id/chunk_id', fk_skipped)
            if resolved:
                _log.info('load_quotes: resolved %d quotes onto active chunks', resolved)
        except Exception:
            conn.rollback()
            raise
        count = cur.execute('SELECT COUNT(*) FROM quotes').fetchone()[0]
    return {'quotes': count, 'resolved_quotes': resolved}
