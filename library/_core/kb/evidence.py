#!/usr/bin/env python3
"""Write KB evidence rows from normalized candidates into SQLite."""
from library.config import DB_PATH, KB_CANDIDATES_NORM
from library.db import connect, get_id
from library.utils import load_json


def write_evidence():
    """Main evidence writer. Returns counts dict."""
    data = load_json(KB_CANDIDATES_NORM, default={})
    with connect() as conn:
        cur = conn.cursor()
        cur.execute('DELETE FROM theme_evidence')
        cur.execute('DELETE FROM principle_evidence')
        cur.execute('DELETE FROM pattern_evidence')

        for item in data.get('themes', []):
            theme_id = get_id(cur, 'themes', 'theme_name', item['theme_name'])
            if theme_id:
                cur.execute(
                    'INSERT INTO theme_evidence (theme_id, chunk_id, note) VALUES (?, ?, ?)',
                    (theme_id, item['chunk_id'], ', '.join(item.get('matched_terms', []))),
                )

        for item in data.get('principles', []):
            pid = get_id(cur, 'principles', 'principle_name', item['principle_name'])
            if pid:
                cur.execute(
                    'INSERT INTO principle_evidence (principle_id, chunk_id, note) VALUES (?, ?, ?)',
                    (pid, item['chunk_id'], ', '.join(item.get('matched_terms', []))),
                )

        for item in data.get('patterns', []):
            pid = get_id(cur, 'patterns', 'pattern_name', item['pattern_name'])
            if pid:
                cur.execute(
                    'INSERT INTO pattern_evidence (pattern_id, chunk_id, note) VALUES (?, ?, ?)',
                    (pid, item['chunk_id'], ', '.join(item.get('matched_terms', []))),
                )

        counts = {
            'theme_evidence': cur.execute('SELECT COUNT(*) FROM theme_evidence').fetchone()[0],
            'principle_evidence': cur.execute('SELECT COUNT(*) FROM principle_evidence').fetchone()[0],
            'pattern_evidence': cur.execute('SELECT COUNT(*) FROM pattern_evidence').fetchone()[0],
        }
    return counts
