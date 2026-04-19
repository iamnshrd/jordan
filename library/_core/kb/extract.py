#!/usr/bin/env python3
"""Extract KB candidates from document chunks using keyword + phrase matching rules.

When pymorphy3 is installed, Russian words are lemmatized before matching,
which significantly reduces false negatives from inflected forms.
"""
import logging
import re
import sys

from library.config import KB_CANDIDATES, VENDOR
from library.db import connect
from library.utils import save_json, get_threshold

log = logging.getLogger('jordan')

_SENTINEL = object()
_morph = None
_morph_loaded = False

_RU_FALLBACK_SUFFIXES = sorted([
    'иями', 'ями', 'ами', 'иями', 'остью', 'остями', 'остях',
    'ение', 'ений', 'ению', 'ением', 'ениях',
    'ировать', 'ировать', 'аться', 'яться', 'иться',
    'ного', 'нему', 'тельн', 'тельны', 'тельный',
    'ости', 'остью', 'ость', 'иями', 'иями',
    'ского', 'скому', 'скими', 'ская', 'ские',
    'ого', 'его', 'ому', 'ему', 'ыми', 'ими',
    'иях', 'иях', 'иях', 'ах', 'ях', 'ия', 'ие', 'ий', 'ый', 'ой',
    'ая', 'яя', 'ую', 'юю', 'ое', 'ее',
    'ов', 'ев', 'ом', 'ем', 'ам', 'ям', 'ах', 'ях',
    'ы', 'и', 'а', 'я', 'о', 'е', 'у', 'ю',
], key=len, reverse=True)


def _get_morph():
    """Lazy-load pymorphy3 for Russian lemmatization. Returns None if unavailable."""
    global _morph, _morph_loaded
    if _morph_loaded:
        return _morph
    _morph_loaded = True
    try:
        vendor_path = str(VENDOR)
        if VENDOR.exists() and vendor_path not in sys.path:
            sys.path.insert(0, vendor_path)
        import pymorphy3
        _morph = pymorphy3.MorphAnalyzer()
        log.debug('pymorphy3 loaded for lemmatization')
    except ImportError:
        log.info('pymorphy3 not installed; using heuristic stemming')
        _morph = None
    return _morph


def _simple_stem_ru(word: str) -> str:
    """Very small Russian fallback stemmer for offline environments."""
    w = word.lower()
    if len(w) <= 4:
        return w
    for suffix in _RU_FALLBACK_SUFFIXES:
        if w.endswith(suffix) and len(w) - len(suffix) >= 4:
            return w[:-len(suffix)]
    return w


def _lemmatize_ru(word: str) -> str:
    """Return the normal form of a Russian word, or the word itself."""
    morph = _get_morph()
    if morph is None:
        return _simple_stem_ru(word)
    parsed = morph.parse(word)
    return parsed[0].normal_form if parsed else word.lower()


def _is_cyrillic(word: str) -> bool:
    return any('\u0400' <= ch <= '\u04ff' for ch in word)


def _lemmatize_text(text: str) -> str:
    """Lemmatize Russian words in text, leave English as-is (lowered)."""
    words = re.findall(r'[\w]+', text.lower())
    result = []
    for w in words:
        if _is_cyrillic(w) and len(w) >= 3:
            result.append(_lemmatize_ru(w))
        else:
            result.append(w)
    return ' '.join(result)

THEME_RULES = {
    'meaning': {
        'words': ['смысл', 'meaning', 'purpose'],
        'phrases': ['потеря смысла', 'утрата направления', 'loss of meaning', 'отсутствие цели'],
    },
    'responsibility': {
        'words': ['ответствен', 'responsibility', 'burden'],
        'phrases': ['принять ответственность', 'добровольное бремя', 'voluntary burden'],
    },
    'order-and-chaos': {
        'words': ['хаос', 'поряд', 'chaos', 'order'],
        'phrases': ['между порядком и хаосом', 'order and chaos', 'распад структуры'],
    },
    'truth': {
        'words': ['правд', 'truth', 'лож', 'lie'],
        'phrases': ['говорить правду', 'tell the truth', 'самообман', 'self-deception'],
    },
    'resentment': {
        'words': ['resentment', 'обид', 'озлоб', 'гореч'],
        'phrases': ['скрытая обида', 'невысказанная горечь', 'accumulated resentment'],
    },
    'suffering': {
        'words': ['страдан', 'suffering', 'pain'],
        'phrases': ['неизбежное страдание', 'unavoidable suffering', 'структурное страдание'],
    },
}

PRINCIPLE_RULES = {
    'tell-the-truth-or-at-least-dont-lie': {
        'words': ['говорить правду', 'truth', 'lie'],
        'phrases': ['не лгите хотя бы', 'tell the truth or at least', 'перестать лгать себе'],
    },
    'clean-up-what-is-in-front-of-you': {
        'words': ['комнат', 'clean', 'order', 'убер'],
        'phrases': ['убери свою комнату', 'clean your room', 'локальный порядок'],
    },
    'take-responsibility-before-blame': {
        'words': ['ответствен', 'blame', 'вина мира'],
        'phrases': ['прежде чем обвинять', 'before you blame', 'взять на себя ответственность'],
    },
}

PATTERN_RULES = {
    'avoidance-loop': {
        'words': ['избег', 'avoid', 'прят'],
        'phrases': ['петля избегания', 'avoidance loop', 'откладывание решения'],
    },
    'resentment-loop': {
        'words': ['resentment', 'обид', 'гореч'],
        'phrases': ['петля обиды', 'resentment loop', 'горечь нарастает'],
    },
    'aimlessness': {
        'words': ['без цели', 'aimless', 'цель', 'direction'],
        'phrases': ['утрата цели', 'lack of aim', 'нет направления'],
    },
}

_word_boundary_cache: dict[str, re.Pattern] = {}


def _count_occurrences(text: str, needle: str) -> int:
    """Count non-overlapping word-boundary occurrences of *needle* in *text*.

    For short needles (single words), enforces word boundaries to avoid
    false matches like 'order' inside 'disorder'. For multi-word phrases
    or Cyrillic stems (typically used as prefixes), uses substring matching.
    """
    lower_needle = needle.lower()
    is_single_ascii = ' ' not in lower_needle and not _is_cyrillic(lower_needle)
    if is_single_ascii and len(lower_needle) >= 3:
        if lower_needle not in _word_boundary_cache:
            _word_boundary_cache[lower_needle] = re.compile(
                r'\b' + re.escape(lower_needle) + r'\b', re.IGNORECASE,
            )
        return len(_word_boundary_cache[lower_needle].findall(text))
    lower = text.lower()
    count = 0
    start = 0
    while True:
        pos = lower.find(lower_needle, start)
        if pos == -1:
            break
        count += 1
        start = pos + len(lower_needle)
    return count


_lemma_phrase_cache: dict[str, str] = {}


def _lemmatize_phrase_cached(phrase: str) -> str:
    """Lemmatize a short phrase with caching."""
    if phrase not in _lemma_phrase_cache:
        _lemma_phrase_cache[phrase] = _lemmatize_text(phrase)
    return _lemma_phrase_cache[phrase]


def candidates_for_rules(text, rules, *, lemmatized: str | None = _SENTINEL):
    """Return scored candidate matches using substring + optional lemma matching.

    Parameters
    ----------
    text : str
        Raw chunk text.
    rules : dict
        Extraction rules.
    lemmatized : str or None
        Pre-computed lemmatized text. Pass None to skip lemma matching,
        or omit to auto-compute (backward compat).
    """
    phrase_bonus = get_threshold('extract_phrase_weight_bonus', 2.0)
    lower = text.lower()
    if lemmatized is _SENTINEL:
        lemmatized = _lemmatize_text(text) if _get_morph() is not None else None

    hits = []
    for name, rule in rules.items():
        words = rule if isinstance(rule, list) else rule.get('words', [])
        phrases = [] if isinstance(rule, list) else rule.get('phrases', [])

        matched_words = []
        tf_cache: dict[str, int] = {}
        for w in words:
            w_lower = w.lower()
            is_ascii_word = ' ' not in w_lower and not _is_cyrillic(w_lower) and len(w_lower) >= 3
            if is_ascii_word:
                tf = _count_occurrences(text, w)
                if tf > 0:
                    matched_words.append(w)
                    tf_cache[w] = tf
                elif lemmatized is not None:
                    if w_lower in lemmatized:
                        matched_words.append(w)
            else:
                if w_lower in lower:
                    matched_words.append(w)
                elif lemmatized is not None:
                    lemma_w = _lemmatize_ru(w) if _is_cyrillic(w) else w_lower
                    if lemma_w in lemmatized:
                        matched_words.append(w)

        matched_phrases = []
        for p in phrases:
            if p.lower() in lower:
                matched_phrases.append(p)
            elif lemmatized is not None:
                lemma_p = _lemmatize_phrase_cached(p)
                if lemma_p in lemmatized:
                    matched_phrases.append(p)

        if not matched_words and not matched_phrases:
            continue

        weight = 0.0
        for w in matched_words:
            tf = tf_cache.get(w) or _count_occurrences(text, w)
            weight += max(tf, 1)
        for p in matched_phrases:
            tf = _count_occurrences(text, p)
            weight += max(tf, 1) * phrase_bonus

        hits.append({
            'name': name,
            'matched_terms': matched_words + matched_phrases,
            'matched_phrases': matched_phrases,
            'weight': round(weight, 2),
        })
    return hits


def extract():
    """Main extraction. Returns dict with counts."""
    out = {
        'themes': [],
        'principles': [],
        'patterns': [],
    }
    use_lemma = _get_morph() is not None
    batch_size = 500
    offset = 0
    with connect() as conn:
        while True:
            rows = conn.cursor().execute(
                'SELECT dc.id, dc.document_id, dc.chunk_index, dc.content '
                'FROM document_chunks dc '
                'JOIN documents d ON d.id = dc.document_id '
                'WHERE dc.revision_id = d.active_revision_id '
                'ORDER BY dc.id LIMIT ? OFFSET ?',
                (batch_size, offset),
            ).fetchall()
            if not rows:
                break
            offset += len(rows)
            for chunk_id, document_id, chunk_index, content in rows:
                if not content:
                    continue
                text = re.sub(r'\s+', ' ', content).strip()
                lemmatized = _lemmatize_text(text) if use_lemma else None
                for hit in candidates_for_rules(text, THEME_RULES, lemmatized=lemmatized):
                    out['themes'].append({
                        'chunk_id': chunk_id,
                        'document_id': document_id,
                        'chunk_index': chunk_index,
                        'theme_name': hit['name'],
                        'matched_terms': hit['matched_terms'],
                        'weight': hit['weight'],
                        'excerpt': text[:500],
                    })
                for hit in candidates_for_rules(text, PRINCIPLE_RULES, lemmatized=lemmatized):
                    out['principles'].append({
                        'chunk_id': chunk_id,
                        'document_id': document_id,
                        'chunk_index': chunk_index,
                        'principle_name': hit['name'],
                        'matched_terms': hit['matched_terms'],
                        'weight': hit['weight'],
                        'excerpt': text[:500],
                    })
                for hit in candidates_for_rules(text, PATTERN_RULES, lemmatized=lemmatized):
                    out['patterns'].append({
                        'chunk_id': chunk_id,
                        'document_id': document_id,
                        'chunk_index': chunk_index,
                        'pattern_name': hit['name'],
                        'matched_terms': hit['matched_terms'],
                        'weight': hit['weight'],
                        'excerpt': text[:500],
                    })
    save_json(KB_CANDIDATES, out)
    return {k: len(v) for k, v in out.items()}
