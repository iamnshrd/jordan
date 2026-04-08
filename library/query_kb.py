#!/usr/bin/env python3
import argparse
import json
import sqlite3
from pathlib import Path

DB = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/library/jordan_knowledge.db')


def row_to_dict(cur, row):
    return {d[0]: row[i] for i, d in enumerate(cur.description)}


def search_chunks(conn, query, limit=8):
    cur = conn.cursor()
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


def list_table(conn, table, limit=20):
    cur = conn.cursor()
    cur.execute(f'SELECT * FROM {table} LIMIT ?', (limit,))
    return [row_to_dict(cur, row) for row in cur.fetchall()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--query', default='')
    ap.add_argument('--limit', type=int, default=8)
    ap.add_argument('--table', default='')
    args = ap.parse_args()

    conn = sqlite3.connect(DB)
    out = {}
    if args.query:
        out['chunk_hits'] = search_chunks(conn, args.query, args.limit)
    if args.table:
        out['table_rows'] = list_table(conn, args.table, args.limit)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    conn.close()


if __name__ == '__main__':
    main()
