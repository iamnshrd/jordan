#!/usr/bin/env python3
"""SQLite helpers shared across the project.

Provides a context-managed connection factory, safe table listing,
common row-conversion utilities, and automatic schema migration on connect.
"""
from __future__ import annotations

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
    'chunk_embeddings',
})


def ensure_schema(conn):
    """Run pending migrations if the DB is behind the latest version."""
    from library._core.kb.migrate import LATEST_VERSION, get_schema_version, migrate_up
    if get_schema_version(conn) < LATEST_VERSION:
        migrate_up(conn)


@contextmanager
def connect(db_path=None, auto_migrate: bool = True):
    """Yield a sqlite3 connection, committing on success.

    When *auto_migrate* is True (default), ``ensure_schema`` is called once
    after opening the connection to bring the DB up to the latest version.
    """
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON')
    try:
        if auto_migrate:
            ensure_schema(conn)
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
