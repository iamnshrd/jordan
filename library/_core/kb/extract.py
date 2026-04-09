#!/usr/bin/env python3
"""Extract KB candidates from document chunks using keyword matching rules."""
import re

from library.config import DB_PATH, KB_CANDIDATES
from library.db import connect
from library.utils import save_json

THEME_RULES = {
    'meaning': ['смысл', 'meaning', 'purpose'],
    'responsibility': ['ответствен', 'responsibility', 'burden'],
    'order-and-chaos': ['хаос', 'поряд', 'chaos', 'order'],
    'truth': ['правд', 'truth', 'лож', 'lie'],
    'resentment': ['resentment', 'обид', 'озлоб', 'гореч'],
    'suffering': ['страдан', 'suffering', 'pain'],
}
PRINCIPLE_RULES = {
    'tell-the-truth-or-at-least-dont-lie': ['говорить правду', 'truth', 'lie'],
    'clean-up-what-is-in-front-of-you': ['комнат', 'clean', 'order', 'убер'],
    'take-responsibility-before-blame': ['ответствен', 'blame', 'вина мира'],
}
PATTERN_RULES = {
    'avoidance-loop': ['избег', 'avoid', 'прят'],
    'resentment-loop': ['resentment', 'обид', 'гореч'],
    'aimlessness': ['без цели', 'aimless', 'цель', 'direction'],
}


def candidates_for_rules(text, rules):
    lower = text.lower()
    hits = []
    for name, needles in rules.items():
        matched = [n for n in needles if n in lower]
        if matched:
            hits.append({'name': name, 'matched_terms': matched})
    return hits


def extract():
    """Main extraction. Returns dict with counts."""
    with connect() as conn:
        cur = conn.cursor()
        rows = cur.execute('SELECT id, document_id, chunk_index, content FROM document_chunks').fetchall()
    out = {
        'themes': [],
        'principles': [],
        'patterns': [],
    }
    for chunk_id, document_id, chunk_index, content in rows:
        text = re.sub(r'\s+', ' ', content).strip()
        for hit in candidates_for_rules(text, THEME_RULES):
            out['themes'].append({
                'chunk_id': chunk_id,
                'document_id': document_id,
                'chunk_index': chunk_index,
                'theme_name': hit['name'],
                'matched_terms': hit['matched_terms'],
                'excerpt': text[:500],
            })
        for hit in candidates_for_rules(text, PRINCIPLE_RULES):
            out['principles'].append({
                'chunk_id': chunk_id,
                'document_id': document_id,
                'chunk_index': chunk_index,
                'principle_name': hit['name'],
                'matched_terms': hit['matched_terms'],
                'excerpt': text[:500],
            })
        for hit in candidates_for_rules(text, PATTERN_RULES):
            out['patterns'].append({
                'chunk_id': chunk_id,
                'document_id': document_id,
                'chunk_index': chunk_index,
                'pattern_name': hit['name'],
                'matched_terms': hit['matched_terms'],
                'excerpt': text[:500],
            })
    save_json(KB_CANDIDATES, out)
    return {k: len(v) for k, v in out.items()}
