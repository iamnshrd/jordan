#!/usr/bin/env python3
import argparse
import json
import sqlite3
from pathlib import Path

DB = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/jordan_knowledge.db')
ARBITRATION = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/source_arbitration_rules.json')
DOC_SOURCE_HINTS = {
    1: '12-rules',
    2: 'maps-of-meaning',
    3: 'beyond-order',
}


def row_to_dict(cur, row):
    return {d[0]: row[i] for i, d in enumerate(cur.description)}


def fts_query(text):
    words = [w for w in ''.join(ch if ch.isalnum() or ch.isspace() else ' ' for ch in text.lower()).split() if len(w) >= 3]
    return ' OR '.join(words[:8]) if words else 'meaning'


def search_chunks(cur, query, limit=5):
    cur.execute(
        """
        SELECT dc.id, dc.chunk_index, snippet(document_chunks_fts, 0, '[', ']', ' … ', 16) AS snippet
        FROM document_chunks_fts fts
        JOIN document_chunks dc ON dc.id = fts.rowid
        WHERE document_chunks_fts MATCH ?
        LIMIT ?
        """,
        (fts_query(query), limit),
    )
    return [row_to_dict(cur, row) for row in cur.fetchall()]


def search_quotes(cur, query, limit=4):
    cur.execute('SELECT id, quote_text FROM quotes WHERE quote_text LIKE ? LIMIT ?', (f'%{query}%', limit))
    return [row_to_dict(cur, row) for row in cur.fetchall()]


def top_linked(cur, query, evidence_table, join_table, fk_col, name_col, content_join=False, limit=5):
    if content_join:
        sql = f'''
        SELECT t.{name_col} AS name, COUNT(*) AS hits
        FROM {evidence_table} e
        JOIN {join_table} t ON t.id = e.{fk_col}
        JOIN document_chunks dc ON dc.id = e.chunk_id
        WHERE dc.content LIKE ?
        GROUP BY t.{name_col}
        ORDER BY hits DESC
        LIMIT ?
        '''
    else:
        sql = f'''
        SELECT t.{name_col} AS name, COUNT(*) AS hits
        FROM {evidence_table} e
        JOIN {join_table} t ON t.id = e.{fk_col}
        GROUP BY t.{name_col}
        ORDER BY hits DESC
        LIMIT ?
        '''
    if content_join:
        cur.execute(sql, (f'%{query}%', limit))
    else:
        cur.execute(sql, (limit,))
    return [row_to_dict(cur, row) for row in cur.fetchall()]


THEME_KEYWORDS = {
    'meaning': ['смысл', 'meaning', 'purpose', 'direction', 'направление', 'цель'],
    'responsibility': ['ответствен', 'долг', 'burden', 'обязан'],
    'order-and-chaos': ['хаос', 'беспоряд', 'дисциплин', 'порядок', 'structure'],
    'truth': ['правд', 'лож', 'честн', 'truth', 'lie'],
    'resentment': ['обид', 'гореч', 'resentment', 'злость'],
    'suffering': ['страдан', 'pain', 'suffering', 'боль'],
}
PROBLEM_ROUTES = {
    'meaning-loss': {
        'if_any': ['смысл', 'направление', 'цель', 'direction', 'purpose', 'дисциплин'],
        'boost_themes': {'meaning': 180, 'order-and-chaos': 120, 'responsibility': 80},
        'boost_principles': {'clean-up-what-is-in-front-of-you': 120, 'take-responsibility-before-blame': 90},
        'boost_patterns': {'aimlessness': 180, 'avoidance-loop': 60},
        'downweight_themes': {'truth': 120}
    },
    'self-deception': {
        'if_any': ['вру', 'лож', 'самообман', 'честн', 'truth'],
        'boost_themes': {'truth': 180},
        'boost_principles': {'tell-the-truth-or-at-least-dont-lie': 180},
        'boost_patterns': {'avoidance-loop': 60},
        'downweight_themes': {}
    },
    'resentment': {
        'if_any': ['обид', 'гореч', 'несправед', 'resentment', 'злость'],
        'boost_themes': {'resentment': 220, 'responsibility': 60},
        'boost_principles': {'take-responsibility-before-blame': 120},
        'boost_patterns': {'resentment-loop': 200, 'avoidance-loop': 40},
        'downweight_themes': {}
    },
    'shame-self-contempt': {
        'if_any': ['стыд', 'никчем', 'омерзен', 'ненавижу себя', 'self-contempt', 'отвращение к себе'],
        'boost_themes': {'suffering': 220, 'truth': 30, 'responsibility': 40},
        'boost_principles': {'tell-the-truth-or-at-least-dont-lie': 150, 'take-responsibility-before-blame': 40},
        'boost_patterns': {'avoidance-loop': 130},
        'downweight_themes': {'resentment': 40, 'truth': 40}
    },
    'relationship-conflict': {
        'if_any': ['отношен', 'партнер', 'жена', 'муж', 'ссор', 'конфликт', 'брак'],
        'boost_themes': {'responsibility': 260, 'truth': 110, 'resentment': 10},
        'boost_principles': {'tell-the-truth-or-at-least-dont-lie': 190, 'take-responsibility-before-blame': 50},
        'boost_patterns': {'resentment-loop': 160},
        'downweight_themes': {'resentment': 80}
    },
    'avoidance-paralysis': {
        'if_any': ['не могу начать', 'паралич', 'избегаю', 'откладываю', 'прокраст', 'avoid'],
        'boost_themes': {'order-and-chaos': 110, 'responsibility': 90},
        'boost_principles': {'clean-up-what-is-in-front-of-you': 140, 'take-responsibility-before-blame': 90},
        'boost_patterns': {'avoidance-loop': 220, 'aimlessness': 60},
        'downweight_themes': {'truth': 40}
    },
    'career-vocation': {
        'if_any': ['работ', 'карьер', 'призвание', 'vocation', 'путь', 'профес'],
        'boost_themes': {'meaning': 220, 'responsibility': 140},
        'boost_principles': {'take-responsibility-before-blame': 110, 'clean-up-what-is-in-front-of-you': 70},
        'boost_patterns': {'aimlessness': 180},
        'downweight_themes': {'truth': 140}
    },
    'parenting-overprotection': {
        'if_any': ['ребен', 'дет', 'воспит', 'родител', 'parenting', 'тирана'],
        'boost_themes': {'responsibility': 220, 'order-and-chaos': 90},
        'boost_principles': {'clean-up-what-is-in-front-of-you': 100, 'tell-the-truth-or-at-least-dont-lie': 40},
        'boost_patterns': {'avoidance-loop': 80},
        'downweight_themes': {'truth': 140}
    },
    'addiction-chaos': {
        'if_any': ['зависим', 'алкогол', 'наркот', 'хаос', 'спиваюсь', 'addiction'],
        'boost_themes': {'order-and-chaos': 180, 'suffering': 120, 'responsibility': 70},
        'boost_principles': {'clean-up-what-is-in-front-of-you': 120, 'take-responsibility-before-blame': 80},
        'boost_patterns': {'avoidance-loop': 150},
        'downweight_themes': {}
    }
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


def route_adjustments(question):
    q = question.lower()
    adj = {
        'themes': {},
        'principles': {},
        'patterns': {},
    }
    for route in PROBLEM_ROUTES.values():
        if any(x in q for x in route['if_any']):
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


def load_arbitration_rules():
    if ARBITRATION.exists():
        return json.loads(ARBITRATION.read_text()).get('routes', [])
    return []


def infer_preferred_sources(question):
    q = question.lower()
    for route in load_arbitration_rules():
        if any(x in q for x in route.get('if_any', [])):
            return route.get('prefer', ['12-rules', 'beyond-order', 'maps-of-meaning'])
    return ['12-rules', 'beyond-order', 'maps-of-meaning']


def apply_source_preference(rows, preferred_sources):
    order = {name: idx for idx, name in enumerate(preferred_sources)}
    for row in rows:
        source_name = DOC_SOURCE_HINTS.get(row.get('document_id'))
        row['_source_preference'] = order.get(source_name, 999)
    rows.sort(key=lambda x: (x.get('_source_preference', 999), -x.get('_score', 0), -x.get('hits', 0), x.get('name', x.get('id', 0))))
    return rows


def search_quotes_by_keywords(cur, question, selected_names, selected_texts, limit=4):
    q = question.lower()
    route_quote_types = []
    if any(x in q for x in ['смысл', 'направление', 'цель', 'дисциплин', 'не могу начать', 'отклады']):
        route_quote_types = ['discipline-quote', 'principle-quote']
    elif any(x in q for x in ['отношен', 'жена', 'муж', 'партнер', 'конфликт', 'ребен', 'дет', 'воспит', 'родител', 'тирана']):
        route_quote_types = ['relationship-quote', 'resentment-quote', 'principle-quote']
    elif any(x in q for x in ['карьер', 'призвание', 'vocation', 'профес', 'путь']):
        route_quote_types = ['discipline-quote', 'principle-quote']
    elif any(x in q for x in ['стыд', 'позор', 'отвращение к себе']):
        route_quote_types = ['shame-quote', 'principle-quote']
    elif any(x in q for x in ['обид', 'гореч', 'несправед', 'злость']):
        route_quote_types = ['resentment-quote', 'relationship-quote', 'principle-quote']
    else:
        route_quote_types = ['principle-quote', 'discipline-quote', 'relationship-quote', 'shame-quote', 'resentment-quote']

    placeholders = ','.join(['?'] * len(route_quote_types))
    cur.execute(
        f'SELECT id, document_id, quote_text, note, quote_type, theme_name, principle_name, pattern_name FROM quotes WHERE quote_type IN ({placeholders})',
        route_quote_types,
    )
    rows = [row_to_dict(cur, row) for row in cur.fetchall()]

    question_words = [w for w in ''.join(ch if ch.isalnum() or ch.isspace() else ' ' for ch in q).split() if len(w) >= 4]
    for row in rows:
        score = 0
        if row.get('theme_name') in selected_names:
            score += 60
        if row.get('principle_name') in selected_names:
            score += 80
        if row.get('pattern_name') in selected_names:
            score += 40
        if row.get('quote_type') == route_quote_types[0]:
            score += 120
        if any(x in q for x in ['карьер', 'призвание', 'vocation', 'профес', 'путь']):
            if row.get('quote_type') == 'discipline-quote':
                score += 120
            if (row.get('note') or '').startswith('manual'):
                score += 140
        text = (row.get('quote_text') or '').lower()
        for w in question_words:
            if w in text:
                score += 8
        if row.get('quote_type') == 'principle-quote' and row.get('principle_name') == 'tell-the-truth-or-at-least-dont-lie' and not any(x in q for x in ['правд', 'лож', 'самообман', 'честн']):
            score -= 80
        if len(text) > 320:
            score -= 20
        if 'почему бы вам просто' in text:
            score -= 100
        if 'правило 5' in text or 'правило 6' in text or 'правило 8' in text:
            score -= 30
        row['_score'] = score
    preferred_sources = infer_preferred_sources(question)
    rows = apply_source_preference(rows, preferred_sources)

    # ensure clean manual route quotes are not crowded out by noisy extracted fragments
    if route_quote_types and route_quote_types[0] == 'discipline-quote':
        manual = [r for r in rows if (r.get('note') or '').startswith('manual')]
        non_manual = [r for r in rows if not (r.get('note') or '').startswith('manual')]
        rows = manual + non_manual
    elif route_quote_types and route_quote_types[0] in {'relationship-quote', 'shame-quote', 'resentment-quote'}:
        manual = [r for r in rows if (r.get('note') or '').startswith('manual') and r.get('quote_type') == route_quote_types[0]]
        others = [r for r in rows if r not in manual]
        rows = manual + others

    return rows[:limit]


def build_response_bundle(question):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    raw_themes = top_linked(cur, question, 'theme_evidence', 'themes', 'theme_id', 'theme_name', True, 8) or top_linked(cur, question, 'theme_evidence', 'themes', 'theme_id', 'theme_name', False, 8)
    raw_principles = top_linked(cur, question, 'principle_evidence', 'principles', 'principle_id', 'principle_name', True, 8) or top_linked(cur, question, 'principle_evidence', 'principles', 'principle_id', 'principle_name', False, 8)
    raw_patterns = top_linked(cur, question, 'pattern_evidence', 'patterns', 'pattern_id', 'pattern_name', True, 8) or top_linked(cur, question, 'pattern_evidence', 'patterns', 'pattern_id', 'pattern_name', False, 8)
    adj = route_adjustments(question)
    preferred_sources = infer_preferred_sources(question)
    top_themes = score_named_rows(raw_themes, THEME_KEYWORDS, question, adj['themes'])[:5]
    top_principles = score_named_rows(raw_principles, PRINCIPLE_KEYWORDS, question, adj['principles'])[:5]
    top_patterns = score_named_rows(raw_patterns, PATTERN_KEYWORDS, question, adj['patterns'])[:5]
    selected_names = [x['name'] for x in top_themes[:2] + top_principles[:2] + top_patterns[:2]]
    selected_texts = selected_names
    quotes = search_quotes_by_keywords(cur, question, selected_names, selected_texts, 4)
    bundle = {
        'question': question,
        'preferred_sources': preferred_sources,
        'relevant_chunks': search_chunks(cur, question, 5),
        'relevant_quotes': quotes or search_quotes(cur, question, 4),
        'top_themes': top_themes,
        'top_principles': top_principles,
        'top_patterns': top_patterns,
    }
    conn.close()
    return bundle


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    args = ap.parse_args()
    print(json.dumps(build_response_bundle(args.question), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
