"""Retrieval engine -- build a response bundle from the knowledge base.

Restructured from: retrieve_for_prompt.py
"""
from __future__ import annotations

from library.config import (
    canonical_user_id,
    SOURCE_ARBITRATION,
    QUESTION_ARCHETYPES,
    SOURCE_ROLE_PROFILES,
    get_default_store,
    get_doc_source_hints,
    friendly_source_name,
)
from library._core.state_store import StateStore, KEY_USER_STATE, KEY_EFFECTIVENESS
from library.db import connect, row_to_dict
from library.utils import SYNONYM_MAP, load_json, fts_query, timed


_source_role_profiles_cache: dict | None = None

_INTENT_SOURCE_SHORTLISTS: list[tuple[list[str], list[str]]] = [
    (
        ['видени', 'vision', 'план', 'future', 'author', 'направлен', 'цель', 'goal'],
        [
            'academy-between-order-chaos',
            'academy-desire-discipline',
            'success-lecture',
            'beyond-order',
            '12-rules',
            'maps-of-meaning',
        ],
    ),
    (
        ['правд', 'точн', 'жалоб', 'разговор', 'complaint', 'narrat', 'truth'],
        [
            'academy-walled-garden',
            'beyond-order',
            '12-rules',
            'maps-of-meaning',
        ],
    ),
    (
        ['страх', 'fear', 'цен', 'price', 'courage'],
        [
            'academy-fear-catalyst',
            'beyond-order',
            'maps-of-meaning',
            '12-rules',
        ],
    ),
    (
        ['trag', 'траг', 'горе', 'страдан', 'faith', 'bitterness', 'гореч'],
        [
            'academy-faith-tragedy',
            'beyond-order',
            'maps-of-meaning',
            '12-rules',
        ],
    ),
    (
        ['offer', 'предлож', 'higher', 'высш', 'commit', 'обязательств'],
        [
            'academy-higher-vision',
            'beyond-order',
            'academy-between-order-chaos',
            '12-rules',
            'maps-of-meaning',
        ],
    ),
    (
        ['успех', 'successful', 'талант', 'iq', 'conscient', 'успеш'],
        [
            'success-lecture',
            'academy-between-order-chaos',
            'academy-desire-discipline',
            'beyond-order',
            '12-rules',
        ],
    ),
]


def _get_source_role_profiles() -> dict:
    global _source_role_profiles_cache
    if _source_role_profiles_cache is None:
        _source_role_profiles_cache = load_json(SOURCE_ROLE_PROFILES, default={})
    return _source_role_profiles_cache


THEME_KEYWORDS = {
    'meaning': ['смысл', 'meaning', 'purpose', 'direction', 'направление', 'цель'],
    'responsibility': ['ответствен', 'долг', 'burden', 'обязан'],
    'order-and-chaos': ['хаос', 'беспоряд', 'дисциплин', 'порядок', 'structure'],
    'truth': ['правд', 'лож', 'честн', 'truth', 'lie'],
    'resentment': ['обид', 'гореч', 'resentment', 'злость'],
    'suffering': ['страдан', 'pain', 'suffering', 'боль'],
}

PROBLEM_ROUTES = {
    'self-deception': {
        'boost_themes': {'truth': 180},
        'boost_principles': {'tell-the-truth-or-at-least-dont-lie': 180},
        'boost_patterns': {'avoidance-loop': 60},
        'downweight_themes': {},
    },
    'resentment': {
        'boost_themes': {'resentment': 220, 'responsibility': 60},
        'boost_principles': {'take-responsibility-before-blame': 120},
        'boost_patterns': {'resentment-loop': 200, 'avoidance-loop': 40},
        'downweight_themes': {},
    },
    'shame-self-contempt': {
        'boost_themes': {'suffering': 220, 'truth': 30, 'responsibility': 40},
        'boost_principles': {'tell-the-truth-or-at-least-dont-lie': 150, 'take-responsibility-before-blame': 40},
        'boost_patterns': {'avoidance-loop': 130},
        'downweight_themes': {'resentment': 40, 'truth': 40},
    },
    'relationship-maintenance': {
        'boost_themes': {'responsibility': 260, 'truth': 110, 'resentment': 10},
        'boost_principles': {'tell-the-truth-or-at-least-dont-lie': 190, 'take-responsibility-before-blame': 50},
        'boost_patterns': {'resentment-loop': 160},
        'downweight_themes': {'resentment': 80},
    },
    'avoidance-paralysis': {
        'boost_themes': {'order-and-chaos': 110, 'responsibility': 90},
        'boost_principles': {'clean-up-what-is-in-front-of-you': 140, 'take-responsibility-before-blame': 90},
        'boost_patterns': {'avoidance-loop': 220, 'aimlessness': 60},
        'downweight_themes': {'truth': 40},
    },
    'career-vocation': {
        'boost_themes': {'meaning': 220, 'order-and-chaos': 120, 'responsibility': 140},
        'boost_principles': {'take-responsibility-before-blame': 110, 'clean-up-what-is-in-front-of-you': 120},
        'boost_patterns': {'aimlessness': 180, 'avoidance-loop': 60},
        'downweight_themes': {'truth': 140},
    },
    'parenting-overprotection': {
        'boost_themes': {'responsibility': 220, 'order-and-chaos': 90},
        'boost_principles': {'clean-up-what-is-in-front-of-you': 100, 'tell-the-truth-or-at-least-dont-lie': 40},
        'boost_patterns': {'avoidance-loop': 80},
        'downweight_themes': {'truth': 140},
    },
    'addiction-chaos': {
        'boost_themes': {'order-and-chaos': 180, 'suffering': 120, 'responsibility': 70},
        'boost_principles': {'clean-up-what-is-in-front-of-you': 120, 'take-responsibility-before-blame': 80},
        'boost_patterns': {'avoidance-loop': 150},
        'downweight_themes': {},
    },
}

PRINCIPLE_KEYWORDS = {
    'take-responsibility-before-blame': ['ответствен', 'обязан', 'вина', 'agency'],
    'clean-up-what-is-in-front-of-you': ['дисциплин', 'комнат', 'порядок', 'structure'],
    'tell-the-truth-or-at-least-dont-lie': ['правд', 'лож', 'честн'],
}

PATTERN_KEYWORDS = {
    'aimlessness': ['смысл', 'направление', 'цель', 'direction', 'aimless'],
    'avoidance-loop': ['избег', 'avoid', 'отклады', 'прокраст'],
    'resentment-loop': ['обид', 'гореч', 'resentment'],
}


def _escape_like(s: str) -> str:
    """Escape special LIKE characters for SQLite."""
    return s.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def _normalize_search_text(text: str) -> tuple[str, str]:
    raw = ' '.join(
        ''.join(
            ch if ch.isalnum() or ch.isspace() else ' '
            for ch in (text or '').lower()
        ).split()
    )
    if not raw:
        return '', ''
    try:
        from library._core.kb.extract import _lemmatize_text
        return raw, _lemmatize_text(raw)
    except Exception:
        return raw, raw


def _query_terms(text: str, min_len: int = 4) -> list[str]:
    raw, lemma = _normalize_search_text(text)
    terms: list[str] = []
    seen: set[str] = set()
    for source in (raw.split(), lemma.split()):
        for token in source:
            if len(token) < min_len or token in seen:
                continue
            seen.add(token)
            terms.append(token)
    for token in list(terms):
        for synonym in SYNONYM_MAP.get(token, [])[:3]:
            synonym = synonym.lower().strip()
            if len(synonym) < min_len or synonym in seen:
                continue
            seen.add(synonym)
            terms.append(synonym)
    return terms[:18]


def _score_text_match(text: str, terms: list[str], *,
                      raw_query: str = '', lemma_query: str = '') -> int:
    if not text:
        return 0
    raw_text, lemma_text = _normalize_search_text(text)
    score = 0
    for term in terms:
        if term in raw_text:
            score += 16 if len(term) >= 7 else 11
        elif term in lemma_text:
            score += 9
    if raw_query and raw_query in raw_text:
        score += 24
    if lemma_query and lemma_query in lemma_text and lemma_query != raw_query:
        score += 12
    return score


def _source_order(preferred_sources: list[str]) -> dict[str, int]:
    return {name: idx for idx, name in enumerate(preferred_sources or [])}


def _intent_specific_sources(question: str) -> list[str] | None:
    q = (question or '').lower()
    for markers, shortlist in _INTENT_SOURCE_SHORTLISTS:
        if any(marker in q for marker in markers):
            return shortlist
    return None


def search_canonical_concepts(cur, question: str, limit: int = 4):
    raw_query, lemma_query = _normalize_search_text(question)
    terms = _query_terms(question)
    rows = cur.execute(
        '''
        SELECT c.id, c.concept_slug, c.concept_name, c.description,
               c.theme_name, c.principle_name, c.pattern_name, c.priority,
               GROUP_CONCAT(DISTINCT a.alias_text) AS aliases,
               COUNT(DISTINCT s.document_id) AS source_count
        FROM canonical_concepts c
        LEFT JOIN canonical_concept_aliases a ON a.concept_id = c.id
        LEFT JOIN canonical_concept_sources s ON s.concept_id = c.id
        GROUP BY c.id
        ORDER BY c.priority DESC, c.concept_name ASC
        '''
    ).fetchall()
    out = []
    for row in rows:
        item = row_to_dict(cur, row)
        text = ' '.join(filter(None, [
            item.get('concept_name'),
            item.get('description'),
            item.get('aliases'),
        ]))
        score = _score_text_match(
            text, terms, raw_query=raw_query, lemma_query=lemma_query,
        )
        for field in ('theme_name', 'principle_name', 'pattern_name'):
            value = (item.get(field) or '').lower()
            if value and value in raw_query:
                score += 18
        score += int(item.get('priority') or 0) * 5
        score += min(int(item.get('source_count') or 0), 5) * 3
        if score <= 0:
            continue
        item['_score'] = score
        out.append(item)
    out.sort(
        key=lambda x: (
            -x.get('_score', 0),
            -x.get('priority', 0),
            -x.get('source_count', 0),
            x.get('concept_name', ''),
        )
    )
    return out[:limit]


def build_expanded_query(question: str, canonical_rows: list[dict]) -> str:
    extras: list[str] = []
    for row in canonical_rows[:2]:
        if row.get('concept_name'):
            extras.append(row['concept_name'])
        aliases = [a.strip() for a in (row.get('aliases') or '').split(',') if a.strip()]
        extras.extend(aliases[:2])
    return ' '.join(part for part in [question, *extras] if part).strip()


def _structured_score(row: dict, question: str, selected_names: list[str],
                      canonical_slugs: set[str],
                      preferred_sources: list[str]) -> tuple[int, int]:
    raw_query, lemma_query = _normalize_search_text(question)
    terms = _query_terms(question)
    text = ' '.join(filter(None, [
        row.get('title'),
        row.get('summary'),
        row.get('response'),
        row.get('concept_name'),
        row.get('section_title'),
        row.get('source_pdf'),
    ]))
    score = _score_text_match(
        text, terms, raw_query=raw_query, lemma_query=lemma_query,
    )
    if row.get('theme_name') in selected_names:
        score += 45
    if row.get('principle_name') in selected_names:
        score += 55
    if row.get('pattern_name') in selected_names:
        score += 35
    if row.get('concept_slug') in canonical_slugs:
        score += 80

    source_name = _row_source_name(row)
    source_pref = _source_order(preferred_sources).get(source_name, 999)
    if source_pref != 999:
        score += max(0, 40 - source_pref * 8)
    return score, source_pref


def search_structured_rows(cur, table: str, label_col: str, question: str,
                           selected_names: list[str],
                           preferred_sources: list[str],
                           canonical_slugs: set[str], limit: int = 4,
                           extra_cols: tuple[str, ...] = ()):
    cols = ', '.join(f'k.{col}' for col in extra_cols)
    if cols:
        cols = ', ' + cols
    rows = cur.execute(
        f'''
        SELECT k.id,
               k.{label_col} AS title,
               k.summary,
               k.theme_name,
               k.principle_name,
               k.pattern_name,
               k.source_document_id,
               k.note,
               d.source_pdf,
               c.concept_slug,
               c.concept_name{cols}
        FROM {table} k
        LEFT JOIN documents d ON d.id = k.source_document_id
        LEFT JOIN canonical_concepts c ON c.id = k.canonical_concept_id
        ORDER BY k.id ASC
        '''
    ).fetchall()
    out = []
    for row in rows:
        item = row_to_dict(cur, row)
        score, source_pref = _structured_score(
            item, question, selected_names, canonical_slugs, preferred_sources,
        )
        if score <= 0:
            continue
        item['_score'] = score
        item['_source_preference'] = source_pref
        out.append(item)
    out.sort(
        key=lambda x: (
            x.get('_source_preference', 999),
            -x.get('_score', 0),
            x.get('title', ''),
        )
    )
    return out[:limit]


def search_chapter_summaries(cur, question: str, selected_names: list[str],
                             preferred_sources: list[str],
                             canonical_slugs: set[str], limit: int = 4):
    rows = cur.execute(
        '''
        SELECT cs.id, cs.document_id AS source_document_id,
               cs.section_title, cs.summary,
               cs.theme_name, cs.principle_name, cs.pattern_name,
               d.source_pdf, c.concept_slug, c.concept_name
        FROM chapter_summaries cs
        JOIN documents d ON d.id = cs.document_id
        LEFT JOIN canonical_concepts c ON c.id = cs.canonical_concept_id
        ORDER BY cs.document_id ASC, cs.id ASC
        '''
    ).fetchall()
    out = []
    for row in rows:
        item = row_to_dict(cur, row)
        score, source_pref = _structured_score(
            item, question, selected_names, canonical_slugs, preferred_sources,
        )
        if item.get('section_title'):
            score += _score_text_match(item['section_title'], _query_terms(question))
        if score <= 0:
            continue
        item['_score'] = score
        item['_source_preference'] = source_pref
        out.append(item)
    out.sort(
        key=lambda x: (
            x.get('_source_preference', 999),
            -x.get('_score', 0),
            x.get('section_title', ''),
        )
    )
    return out[:limit]


# -- core helpers ----------------------------------------------------------

def search_chunks(cur, query, limit=None):
    if limit is None:
        from library.utils import get_threshold
        limit = get_threshold('retrieve_chunk_limit', 5)
    cur.execute(
        """
        SELECT dc.id, dc.chunk_index,
               snippet(document_chunks_fts, 0, '[', ']', ' … ', 16) AS snippet,
               bm25(document_chunks_fts) AS rank
        FROM document_chunks_fts fts
        JOIN document_chunks dc ON dc.id = fts.rowid
        JOIN documents d ON d.id = dc.document_id
        WHERE dc.revision_id = d.active_revision_id
          AND document_chunks_fts MATCH ?
        ORDER BY bm25(document_chunks_fts)
        LIMIT ?
        """,
        (fts_query(query), limit),
    )
    return [row_to_dict(cur, row) for row in cur.fetchall()]


def search_quotes(cur, query, limit=None):
    if limit is None:
        from library.utils import get_threshold
        limit = get_threshold('retrieve_quote_limit', 4)
    cur.execute(
        "SELECT q.id, q.quote_text "
        "FROM quotes q "
        "JOIN document_chunks dc ON dc.id = q.chunk_id "
        "JOIN documents d ON d.id = dc.document_id "
        "WHERE dc.revision_id = d.active_revision_id "
        "AND q.quote_text LIKE ? ESCAPE '\\' "
        "LIMIT ?",
        (f'%{_escape_like(query)}%', limit),
    )
    return [row_to_dict(cur, row) for row in cur.fetchall()]


def top_linked(cur, query, evidence_table, join_table, fk_col, name_col,
               content_join=False, limit=5):
    if content_join:
        fts_q = fts_query(query)
        if not fts_q:
            return []
        sql = f'''
        SELECT t.{name_col} AS name,
               t.description AS description,
               COALESCE(SUM(e.weight), COUNT(*)) AS hits,
               COUNT(DISTINCT dc.id) AS matched_chunks
        FROM {evidence_table} e
        JOIN {join_table} t ON t.id = e.{fk_col}
        JOIN document_chunks dc ON dc.id = e.chunk_id
        JOIN documents d ON d.id = dc.document_id
        JOIN document_chunks_fts ON document_chunks_fts.rowid = dc.id
        WHERE dc.revision_id = d.active_revision_id
          AND document_chunks_fts MATCH ?
        GROUP BY t.{name_col}
        ORDER BY hits DESC, matched_chunks DESC, t.{name_col} ASC
        LIMIT ?
        '''
        cur.execute(sql, (fts_q, limit))
    else:
        sql = f'''
        SELECT t.{name_col} AS name,
               t.description AS description,
               COALESCE(SUM(e.weight), COUNT(*)) AS hits
        FROM {evidence_table} e
        JOIN {join_table} t ON t.id = e.{fk_col}
        JOIN document_chunks dc ON dc.id = e.chunk_id
        JOIN documents d ON d.id = dc.document_id
        WHERE dc.revision_id = d.active_revision_id
          AND dc.content LIKE ?
        GROUP BY t.{name_col}
        ORDER BY hits DESC
        LIMIT ?
        '''
        q_words = [_escape_like(w) for w in query.lower().split() if len(w) >= 3]
        if not q_words:
            return []
        like_pattern = '%' + '%'.join(q_words[:3]) + '%'
        cur.execute(sql.replace('LIKE ?', "LIKE ? ESCAPE '\\'"), (like_pattern, limit))
    return [row_to_dict(cur, row) for row in cur.fetchall()]


# -- scoring & routing -----------------------------------------------------

def route_adjustments(question):
    from library._core.runtime.routes import infer_route
    route_name = infer_route(question)
    adj: dict = {'themes': {}, 'principles': {}, 'patterns': {}}
    route = PROBLEM_ROUTES.get(route_name)
    if route:
        for k, v in route.get('boost_themes', {}).items():
            adj['themes'][k] = adj['themes'].get(k, 0) + v
        for k, v in route.get('boost_principles', {}).items():
            adj['principles'][k] = adj['principles'].get(k, 0) + v
        for k, v in route.get('boost_patterns', {}).items():
            adj['patterns'][k] = adj['patterns'].get(k, 0) + v
        for k, v in route.get('downweight_themes', {}).items():
            adj['themes'][k] = adj['themes'].get(k, 0) - v
    return adj


def score_named_rows(rows, keyword_map, question, adjustments=None):
    q = question.lower()
    adjustments = adjustments or {}
    scored = []
    for row in rows:
        name = row['name']
        score = int((row.get('hits', 0)) ** 0.5 * 20)
        for kw in keyword_map.get(name, []):
            if kw in q:
                score += 50
        score += adjustments.get(name, 0)
        scored.append({**row, '_score': score})
    scored.sort(key=lambda x: (-x['_score'], -x.get('hits', 0), x['name']))
    return scored


# -- data loaders ----------------------------------------------------------

_archetypes_cache: list | None = None


def load_archetypes():
    global _archetypes_cache
    if _archetypes_cache is None:
        _archetypes_cache = load_json(QUESTION_ARCHETYPES, default=[])
    return _archetypes_cache


def load_user_state(user_id: str = 'default',
                    store: StateStore | None = None):
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    return store.get_json(user_id, KEY_USER_STATE)


def load_effectiveness_data(user_id: str = 'default',
                            store: StateStore | None = None):
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    return store.get_json(user_id, KEY_EFFECTIVENESS)


_route_strength_cache: dict | None = None


def load_source_route_strength():
    global _route_strength_cache
    if _route_strength_cache is not None:
        return _route_strength_cache
    with connect() as conn:
        cur = conn.cursor()
        rows = cur.execute(
            'SELECT source_name, route_name, strength '
            'FROM source_route_strength'
        ).fetchall()
    _route_strength_cache = {(s, r): strength for s, r, strength in rows}
    return _route_strength_cache


def invalidate_route_strength_cache():
    """Clear the cached route strength data (call after DB updates)."""
    global _route_strength_cache
    _route_strength_cache = None


_arbitration_rules_cache: list | None = None


def load_arbitration_rules():
    global _arbitration_rules_cache
    if _arbitration_rules_cache is None:
        data = load_json(SOURCE_ARBITRATION)
        if isinstance(data, dict):
            routes = data.get('routes')
            _arbitration_rules_cache = routes if isinstance(routes, list) else []
        else:
            _arbitration_rules_cache = []
    return _arbitration_rules_cache


# -- source preference -----------------------------------------------------

def _rank_sources_by_profile(route_guess: str) -> list[str]:
    """Rank sources by their suitability for the guessed route using role profiles."""
    profiles = _get_source_role_profiles()
    if not profiles or not route_guess:
        return ['12-rules', 'beyond-order', 'maps-of-meaning']
    scored: list[tuple[str, int]] = []
    for source_name, profile in profiles.items():
        score = 0
        if route_guess in profile.get('best_for', []):
            score += 3
        if route_guess in profile.get('primary_routes', []):
            score += 2
        if route_guess in profile.get('secondary_routes', []):
            score += 1
        if route_guess in profile.get('worst_for', []):
            score -= 2
        scored.append((source_name, score))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return [s[0] for s in scored]


def infer_preferred_sources(question, user_id: str = 'default',
                            store: StateStore | None = None):
    q = question.lower()
    intent_sources = _intent_specific_sources(question)
    if intent_sources:
        return intent_sources
    for arch in load_archetypes():
        if any(x in q for x in arch.get('if_user_says', [])):
            return arch.get('preferred_sources',
                            ['12-rules', 'beyond-order', 'maps-of-meaning'])
    for route in load_arbitration_rules():
        if any(x in q for x in route.get('if_any', [])):
            return route.get('prefer',
                             ['12-rules', 'beyond-order', 'maps-of-meaning'])

    from library._core.runtime.routes import infer_route
    route_guess = infer_route(question)
    if route_guess != 'general':
        profile_ranked = _rank_sources_by_profile(route_guess)
        if profile_ranked:
            return profile_ranked

    state = load_user_state(user_id=user_id, store=store)
    if state.get('dominant_theme') == 'suffering':
        return ['12-rules', 'maps-of-meaning', 'beyond-order']
    if state.get('dominant_theme') == 'meaning':
        return ['beyond-order', '12-rules', 'maps-of-meaning']
    return ['12-rules', 'beyond-order', 'maps-of-meaning']


def _row_source_name(row: dict) -> str:
    if row.get('document_id') is not None:
        source_name = get_doc_source_hints().get(row.get('document_id'), '')
        normalized = friendly_source_name(source_name)
        return normalized or source_name
    if row.get('source_document_id') is not None:
        source_name = get_doc_source_hints().get(row.get('source_document_id'), '')
        normalized = friendly_source_name(source_name)
        if normalized:
            return normalized
    if row.get('source_pdf'):
        return friendly_source_name(row.get('source_pdf'))
    return ''


def apply_source_preference(rows, preferred_sources, question='',
                            user_id: str = 'default',
                            store: StateStore | None = None):
    effect = load_effectiveness_data(user_id=user_id, store=store)
    strength_map = load_source_route_strength()
    order = {name: idx for idx, name in enumerate(preferred_sources)}

    from library._core.runtime.frame import infer_route_name
    route_guess = infer_route_name(question)
    if route_guess == 'general':
        route_guess = ''

    for row in rows:
        source_name = _row_source_name(row)
        route_key = (
            f'{source_name}::{route_guess}'
            if source_name and route_guess else ''
        )
        route_stats = (
            effect.get('source_routes', {}).get(route_key, {})
            if route_key else {}
        )
        helpful = route_stats.get('times_helpful', 0)
        resisted = route_stats.get('times_resisted', 0)
        strength = (
            strength_map.get((source_name, route_guess), 0)
            if source_name and route_guess else 0
        )
        from library.utils import get_threshold
        w_help = get_threshold('effect_helpful_weight', 20)
        w_resist = get_threshold('effect_resisted_weight', 15)
        w_str = get_threshold('effect_strength_weight', 3)
        row['_effect_score'] = helpful * w_help - resisted * w_resist + strength * w_str
        row['_source_preference'] = order.get(source_name, 999)

    rows.sort(key=lambda x: (
        x.get('_source_preference', 999),
        -x.get('_effect_score', 0),
        -x.get('_score', 0),
        -x.get('hits', 0),
        x.get('name', x.get('id', 0)),
    ))
    return rows


# -- keyword-based quote search --------------------------------------------

def search_quotes_by_keywords(cur, question, selected_names, selected_texts,
                              limit=4, user_id: str = 'default',
                              store: StateStore | None = None):
    q = question.lower()

    course_quote_shortlist = []
    if any(x in q for x in ['туман', 'размыт', 'плыть по течению', 'нет жизни', 'нет структуры']):
        course_quote_shortlist = [
            'There is no no-vision option.',
            'A plan is a narrow and focused vision.',
            "If you don't have a life, you're going to be miserable, but you're not depressed. You just don't have a life.",
            'The probability that you need none of the essential domains of life is zero.',
        ]
    elif any(x in q for x in ['жестк', 'расписан', 'график', 'откладываю', 'прокраст']):
        course_quote_shortlist = [
            'Small changes are still necessarily related to the structure of the whole. That\'s what gives them their meaning.',
            'You want things in your life to be worth the trouble.',
            'It doesn\'t matter where you encounter chaos. It just matters that you do encounter it.',
            'Abstract ideas become meaningful when they are implementable.',
        ]

    if course_quote_shortlist:
        placeholders = ','.join(['?'] * len(course_quote_shortlist))
        cur.execute(
            f'SELECT q.id, q.document_id, q.quote_text, q.note, q.quote_type, q.theme_name, q.principle_name, q.pattern_name '
            f'FROM quotes q '
            f'JOIN document_chunks dc ON dc.id = q.chunk_id '
            f'JOIN documents d ON d.id = dc.document_id '
            f'WHERE dc.revision_id = d.active_revision_id '
            f'AND q.quote_text IN ({placeholders})',
            course_quote_shortlist,
        )
        shortlist_rows = [row_to_dict(cur, row) for row in cur.fetchall()]
        if shortlist_rows:
            order = {text: idx for idx, text in enumerate(course_quote_shortlist)}
            shortlist_rows.sort(key=lambda r: order.get(r.get('quote_text'), 999))
            return shortlist_rows[:limit]

    if any(x in q for x in ['смысл', 'направление', 'цель', 'дисциплин',
                             'не могу начать', 'отклады']):
        route_quote_types = ['discipline-quote', 'principle-quote']
    elif any(x in q for x in ['отношен', 'жена', 'муж', 'партнер', 'конфликт',
                               'ребен', 'дет', 'воспит', 'родител', 'тирана']):
        route_quote_types = ['relationship-quote', 'resentment-quote',
                             'principle-quote']
    elif any(x in q for x in ['карьер', 'призвание', 'vocation', 'профес',
                               'путь']):
        route_quote_types = ['discipline-quote', 'principle-quote']
    elif any(x in q for x in ['стыд', 'позор', 'отвращение к себе']):
        route_quote_types = ['shame-quote', 'principle-quote']
    elif any(x in q for x in ['обид', 'гореч', 'несправед', 'злость']):
        route_quote_types = ['resentment-quote', 'relationship-quote',
                             'principle-quote']
    else:
        route_quote_types = ['principle-quote', 'discipline-quote',
                             'relationship-quote', 'shame-quote',
                             'resentment-quote']

    placeholders = ','.join(['?'] * len(route_quote_types))
    cur.execute(
        f'SELECT q.id, q.document_id, q.quote_text, q.note, q.quote_type, '
        f'q.theme_name, q.principle_name, q.pattern_name '
        f'FROM quotes q '
        f'JOIN document_chunks dc ON dc.id = q.chunk_id '
        f'JOIN documents d ON d.id = dc.document_id '
        f'WHERE dc.revision_id = d.active_revision_id '
        f'AND q.quote_type IN ({placeholders})',
        route_quote_types,
    )
    rows = [row_to_dict(cur, row) for row in cur.fetchall()]

    pack_preferred_sources = []
    pack_quote_ids: set = set()
    for arch in load_archetypes():
        if any(x in q for x in arch.get('if_user_says', [])):
            pack_preferred_sources = arch.get('preferred_sources', [])
            route_name = arch.get('archetype_name')
            if route_name:
                row = cur.execute(
                    'SELECT id FROM route_quote_packs '
                    'WHERE route_name=? LIMIT 1',
                    (route_name,),
                ).fetchone()
                if row:
                    pack_id = row[0]
                    pack_quote_ids = {
                        qid for (qid,) in cur.execute(
                            'SELECT quote_id FROM quote_pack_items '
                            'WHERE pack_id=?',
                            (pack_id,),
                        ).fetchall()
                    }
            break

    question_words = [
        w for w in ''.join(
            ch if ch.isalnum() or ch.isspace() else ' ' for ch in q
        ).split()
        if len(w) >= 4
    ]

    for row in rows:
        score = 0
        note = row.get('note') or ''
        text = (row.get('quote_text') or '').lower()
        if row.get('theme_name') in selected_names:
            score += 60
        if row.get('principle_name') in selected_names:
            score += 80
        if row.get('pattern_name') in selected_names:
            score += 40

        if any(x in q for x in ['туман', 'размыт', 'плыть по течению', 'нет жизни', 'нет структуры']):
            if 'manual course quote seed' in note and any(x in text for x in ['no-vision option', 'narrow and focused vision', "don\'t have a life", 'probability that you need none']):
                score += 320

        if any(x in q for x in ['жестк', 'расписан', 'график', 'откладываю', 'прокраст']):
            if 'manual course quote seed' in note and any(x in text for x in ['small changes', 'worth the trouble', 'encounter chaos']):
                score += 320
        if row.get('quote_type') == route_quote_types[0]:
            score += 120
        source_name = _row_source_name(row)
        if row.get('id') in pack_quote_ids:
            score += 160
        if pack_preferred_sources and source_name in pack_preferred_sources:
            score += max(0, 90 - 20 * pack_preferred_sources.index(source_name))
        if any(x in q for x in ['карьер', 'призвание', 'vocation', 'профес',
                                  'путь', 'туман', 'размыт', 'плыть по течению', 'нет жизни', 'нет структуры']):
            if row.get('quote_type') == 'discipline-quote':
                score += 120
            if (row.get('note') or '').startswith('manual'):
                score += 140
            if 'manual course quote seed' in (row.get('note') or ''):
                score += 180

        if any(x in q for x in ['жестк', 'расписан', 'график', 'откладываю', 'прокраст']):
            if 'manual course quote seed' in (row.get('note') or ''):
                score += 180
            if row.get('quote_type') == 'discipline-quote':
                score += 100
        for w in question_words:
            if w in text:
                score += 8
        if (row.get('quote_type') == 'principle-quote'
                and row.get('principle_name') == 'tell-the-truth-or-at-least-dont-lie'
                and not any(x in q for x in ['правд', 'лож', 'самообман', 'честн'])):
            score -= 80
        if len(text) > 320:
            score -= 20
        if 'почему бы вам просто' in text:
            score -= 100
        if 'правило 5' in text or 'правило 6' in text or 'правило 8' in text:
            score -= 30
        row['_score'] = score

    preferred_sources = infer_preferred_sources(question, user_id=user_id,
                                                store=store)
    rows = apply_source_preference(rows, preferred_sources, question,
                                   user_id=user_id, store=store)

    if route_quote_types and route_quote_types[0] == 'discipline-quote':
        manual = [r for r in rows
                  if (r.get('note') or '').startswith('manual')]
        non_manual = [r for r in rows
                      if not (r.get('note') or '').startswith('manual')]
        rows = manual + non_manual
    elif (route_quote_types
          and route_quote_types[0] in {'relationship-quote', 'shame-quote',
                                        'resentment-quote'}):
        manual = [r for r in rows
                  if (r.get('note') or '').startswith('manual')
                  and r.get('quote_type') == route_quote_types[0]]
        others = [r for r in rows if r not in manual]
        rows = manual + others

    return rows[:limit]


# -- main bundle builder ---------------------------------------------------

@timed('retrieve')
def build_response_bundle(question, user_id: str = 'default',
                          store: StateStore | None = None,
                          query_embedding: list[float] | None = None):
    """Build a response bundle with optional hybrid (FTS + embedding) retrieval.

    When *query_embedding* is provided, chunks are retrieved via hybrid search
    (FTS BM25 + cosine similarity re-ranking).  Otherwise, pure FTS is used.
    """
    from library.utils import get_threshold
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    top_limit = get_threshold('retrieve_top_limit', 8)
    with connect() as conn:
        cur = conn.cursor()
        canonical_limit = get_threshold('retrieve_canonical_limit', 4)
        canonical_concepts = search_canonical_concepts(
            cur, question, limit=canonical_limit,
        )
        expanded_question = build_expanded_query(question, canonical_concepts)

        raw_themes = (
            top_linked(cur, expanded_question, 'theme_evidence', 'themes',
                       'theme_id', 'theme_name', True, top_limit)
            or top_linked(cur, expanded_question, 'theme_evidence', 'themes',
                          'theme_id', 'theme_name', False, top_limit)
        )
        raw_principles = (
            top_linked(cur, expanded_question, 'principle_evidence', 'principles',
                       'principle_id', 'principle_name', True, top_limit)
            or top_linked(cur, expanded_question, 'principle_evidence', 'principles',
                          'principle_id', 'principle_name', False, top_limit)
        )
        raw_patterns = (
            top_linked(cur, expanded_question, 'pattern_evidence', 'patterns',
                       'pattern_id', 'pattern_name', True, top_limit)
            or top_linked(cur, expanded_question, 'pattern_evidence', 'patterns',
                          'pattern_id', 'pattern_name', False, top_limit)
        )

        adj = route_adjustments(question)
        preferred_sources = infer_preferred_sources(
            question, user_id=user_id, store=store,
        )

        scored_top = get_threshold('retrieve_scored_top', 5)
        top_themes = score_named_rows(
            raw_themes, THEME_KEYWORDS, question, adj['themes'],
        )[:scored_top]
        top_principles = score_named_rows(
            raw_principles, PRINCIPLE_KEYWORDS, question, adj['principles'],
        )[:scored_top]
        top_patterns = score_named_rows(
            raw_patterns, PATTERN_KEYWORDS, question, adj['patterns'],
        )[:scored_top]

        selected_names = [
            x['name']
            for x in top_themes[:2] + top_principles[:2] + top_patterns[:2]
        ]
        selected_texts = selected_names
        canonical_slugs = {
            row.get('concept_slug')
            for row in canonical_concepts
            if row.get('concept_slug')
        }

        quote_limit = get_threshold('retrieve_quote_limit', 4)
        quotes = search_quotes_by_keywords(
            cur, question, selected_names, selected_texts, quote_limit,
            user_id=user_id, store=store,
        )
        definitions = search_structured_rows(
            cur, 'definitions', 'term_name', question, selected_names,
            preferred_sources, canonical_slugs,
            limit=get_threshold('retrieve_definition_limit', 4),
        )
        claims = search_structured_rows(
            cur, 'claims', 'claim_text', question, selected_names,
            preferred_sources, canonical_slugs,
            limit=get_threshold('retrieve_claim_limit', 4),
        )
        practices = search_structured_rows(
            cur, 'practices', 'practice_name', question, selected_names,
            preferred_sources, canonical_slugs,
            limit=get_threshold('retrieve_practice_limit', 4),
            extra_cols=('difficulty', 'time_horizon'),
        )
        objections = search_structured_rows(
            cur, 'objections', 'objection_name', question, selected_names,
            preferred_sources, canonical_slugs,
            limit=get_threshold('retrieve_objection_limit', 3),
            extra_cols=('response',),
        )
        chapter_summaries = search_chapter_summaries(
            cur, question, selected_names, preferred_sources, canonical_slugs,
            limit=get_threshold('retrieve_chapter_summary_limit', 4),
        )

        if query_embedding is not None:
            from library._core.kb.embeddings import hybrid_search
            h_fts = get_threshold('hybrid_fts_limit', 20)
            h_final = get_threshold('hybrid_final_limit', 5)
            h_alpha = get_threshold('hybrid_alpha', 0.4)
            relevant_chunks = hybrid_search(
                expanded_question, query_embedding,
                fts_limit=h_fts, final_limit=h_final, alpha=h_alpha,
            )
        else:
            chunk_limit = get_threshold('retrieve_chunk_limit', 5)
            relevant_chunks = search_chunks(cur, expanded_question, chunk_limit)

        bundle = {
            'question': question,
            'expanded_question': expanded_question,
            'preferred_sources': preferred_sources,
            'relevant_chunks': relevant_chunks,
            'relevant_quotes': quotes or search_quotes(cur, expanded_question, 4),
            'top_themes': top_themes,
            'top_principles': top_principles,
            'top_patterns': top_patterns,
            'canonical_concepts': canonical_concepts,
            'relevant_definitions': definitions,
            'relevant_claims': claims,
            'relevant_practices': practices,
            'relevant_objections': objections,
            'relevant_chapter_summaries': chapter_summaries,
        }
    return bundle
