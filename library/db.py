#!/usr/bin/env python3
"""SQLite helpers shared across the project.

Provides a context-managed connection factory, safe table listing,
and common row-conversion utilities.
"""
import sqlite3
from contextlib import contextmanager

from library.config import DB_PATH

ALLOWED_TABLES = frozenset({
    'documents', 'document_chunks', 'document_chunks_fts',
    'themes', 'principles', 'patterns', 'intervention_styles',
    'quotes', 'cases', 'argument_frames', 'relationship_patterns',
    'developmental_problems', 'symbolic_motifs', 'intervention_examples',
    'theme_evidence', 'principle_evidence', 'pattern_evidence',
    'source_route_strength', 'bridge_to_action_templates',
    'next_step_library', 'route_quote_packs', 'confidence_tags',
    'archetype_interventions', 'archetype_anti_patterns',
    'case_archetypes', 'case_interventions',
    'motif_cases', 'motif_interventions',
    'pattern_next_steps', 'theme_next_steps',
    'archetype_quote_packs', 'quote_pack_items',
})


@contextmanager
def connect(db_path=None):
    """Yield a sqlite3 connection, committing on success."""
    conn = sqlite3.connect(db_path or DB_PATH)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row_to_dict(cur, row):
    """Convert a sqlite3 row tuple to a dict using cursor description."""
    return {d[0]: row[i] for i, d in enumerate(cur.description)}


def search_chunks(cur, query, limit=5):
    """Full-text search over document_chunks_fts."""
    cur.execute(
        """
        SELECT dc.id, dc.chunk_index,
               snippet(document_chunks_fts, 0, '[', ']', ' … ', 16) AS snippet
        FROM document_chunks_fts fts
        JOIN document_chunks dc ON dc.id = fts.rowid
        WHERE document_chunks_fts MATCH ?
        LIMIT ?
        """,
        (query, limit),
    )
    return [row_to_dict(cur, row) for row in cur.fetchall()]


def search_chunks_with_source(cur, query, limit=8):
    """Full-text search returning source_pdf alongside chunk data."""
    cur.execute(
        """
        SELECT dc.id, d.source_pdf, dc.chunk_index,
               snippet(document_chunks_fts, 0, '[', ']', ' … ', 12) AS snippet
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
    """List rows from *table* with a whitelist guard against SQL injection."""
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Table '{table}' is not in the allowed list")
    cur = conn.cursor()
    cur.execute(f'SELECT * FROM {table} LIMIT ?', (limit,))
    return [row_to_dict(cur, row) for row in cur.fetchall()]


def get_id(cur, table, name_col, name):
    """Fetch the integer id of a named row.  Returns None if missing."""
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Table '{table}' is not in the allowed list")
    cur.execute(f'SELECT id FROM {table} WHERE {name_col} = ?', (name,))
    row = cur.fetchone()
    return row[0] if row else None


def ensure_case(cur, title, summary, intervention_style='manual', risk_note='manual concept harvest'):
    """Insert-or-return a case row."""
    row = cur.execute('SELECT id FROM cases WHERE case_name = ?', (title,)).fetchone()
    if row:
        return row[0]
    cur.execute(
        'INSERT INTO cases (case_name, description, intervention_style, risk_note) VALUES (?, ?, ?, ?)',
        (title, summary, intervention_style, risk_note),
    )
    return cur.lastrowid
