#!/usr/bin/env python3
"""Legacy raw/diagnostic KB query surface.

This module is intentionally kept as a low-level inspection tool for CLI and
audits. The canonical runtime query path used for answer planning is
``query_v3``.
"""
from library.db import connect, row_to_dict, list_table


def search_chunks(conn_or_cur, query, limit=8):
    """Full-text search over document_chunks_fts with BM25 ranking."""
    if hasattr(conn_or_cur, 'cursor'):
        cur = conn_or_cur.cursor()
    else:
        cur = conn_or_cur
    cur.execute(
        """
        SELECT dc.id, d.source_pdf, dc.chunk_index,
               snippet(document_chunks_fts, 0, '[', ']', ' … ', 12) AS snippet,
               bm25(document_chunks_fts) AS rank
        FROM document_chunks_fts fts
        JOIN document_chunks dc ON dc.id = fts.rowid
        JOIN documents d ON d.id = dc.document_id
        WHERE dc.revision_id = d.active_revision_id
          AND document_chunks_fts MATCH ?
        ORDER BY bm25(document_chunks_fts)
        LIMIT ?
        """,
        (query, limit),
    )
    return [row_to_dict(cur, row) for row in cur.fetchall()]


def search_quotes(cur, query, limit):
    cur.execute(
        'SELECT q.id, q.quote_text, q.note '
        'FROM quotes q '
        'JOIN document_chunks dc ON dc.id = q.chunk_id '
        'JOIN documents d ON d.id = dc.document_id '
        'WHERE dc.revision_id = d.active_revision_id '
        'AND q.quote_text LIKE ? LIMIT ?',
        (f'%{query}%', limit),
    )
    return [row_to_dict(cur, row) for row in cur.fetchall()]


def top_evidence(cur, evidence_table, target_table, fk_col, name_col, limit):
    cur.execute(
        f'''SELECT t.{name_col} AS name, COUNT(*) AS hits
            FROM {evidence_table} e
            JOIN {target_table} t ON t.id = e.{fk_col}
            GROUP BY t.{name_col}
            ORDER BY hits DESC
            LIMIT ?''',
        (limit,),
    )
    return [row_to_dict(cur, row) for row in cur.fetchall()]


def query(query_text='', table='', limit=8):
    """Main query entry point. Returns dict with chunk_hits / table_rows / evidence."""
    out = {}
    if query_text:
        from library._core.runtime.retrieve import build_response_bundle
        bundle = build_response_bundle(query_text)
        out['chunk_hits'] = bundle.get('relevant_chunks', [])[:limit]
        out['quotes'] = bundle.get('relevant_quotes', [])[:limit]
        out['top_themes'] = bundle.get('top_themes', [])[:limit]
        out['top_principles'] = bundle.get('top_principles', [])[:limit]
        out['top_patterns'] = bundle.get('top_patterns', [])[:limit]
        out['canonical_concepts'] = bundle.get('canonical_concepts', [])[:limit]
        out['definitions'] = bundle.get('relevant_definitions', [])[:limit]
        out['claims'] = bundle.get('relevant_claims', [])[:limit]
        out['practices'] = bundle.get('relevant_practices', [])[:limit]
        out['objections'] = bundle.get('relevant_objections', [])[:limit]
        out['chapter_summaries'] = bundle.get('relevant_chapter_summaries', [])[:limit]
    if table:
        with connect() as conn:
            out['table_rows'] = list_table(conn, table, limit)
    return out
