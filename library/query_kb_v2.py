#!/usr/bin/env python3
import argparse
import json
import sqlite3
from pathlib import Path

DB = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/jordan_knowledge.db')


def row_to_dict(cur, row):
    return {d[0]: row[i] for i, d in enumerate(cur.description)}


def search_chunks(cur, query, limit):
    cur.execute(
        """
        SELECT dc.id, d.source_pdf, dc.chunk_index, snippet(document_chunks_fts, 0, '[', ']', ' … ', 12) AS snippet
        FROM document_chunks_fts fts
        JOIN document_chunks dc ON dc.id = fts.rowid
        JOIN documents d ON d.id = dc.document_id
        WHERE document_chunks_fts MATCH ?
        LIMIT ?
        """,
        (query, limit),
    )
    return [row_to_dict(cur, row) for row in cur.fetchall()]


def search_quotes(cur, query, limit):
    cur.execute('SELECT id, quote_text, note FROM quotes WHERE quote_text LIKE ? LIMIT ?', (f'%{query}%', limit))
    return [row_to_dict(cur, row) for row in cur.fetchall()]


def top_evidence(cur, evidence_table, target_table, fk_col, name_col, limit):
    cur.execute(
        f'''SELECT t.{name_col} AS name, COUNT(*) AS hits
            FROM {evidence_table} e
            JOIN {target_table} t ON t.id = e.{fk_col}
            GROUP BY t.{name_col}
            ORDER BY hits DESC
            LIMIT ?''',
        (limit,)
    )
    return [row_to_dict(cur, row) for row in cur.fetchall()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--query', default='')
    ap.add_argument('--limit', type=int, default=8)
    args = ap.parse_args()
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    out = {
        'chunks': search_chunks(cur, args.query or 'meaning', args.limit),
        'quotes': search_quotes(cur, args.query or 'правд', args.limit),
        'top_themes': top_evidence(cur, 'theme_evidence', 'themes', 'theme_id', 'theme_name', args.limit),
        'top_principles': top_evidence(cur, 'principle_evidence', 'principles', 'principle_id', 'principle_name', args.limit),
        'top_patterns': top_evidence(cur, 'pattern_evidence', 'patterns', 'pattern_id', 'pattern_name', args.limit),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    conn.close()


if __name__ == '__main__':
    main()
