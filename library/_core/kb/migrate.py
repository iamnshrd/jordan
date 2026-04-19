"""Schema migrations for the knowledge base.

Migrations are immutable and ordered.  Each entry in ``MIGRATIONS`` is a
``(version, callable)`` pair.  ``migrate_up()`` reads the current
``PRAGMA user_version``, applies every migration whose version exceeds it
(in order), and bumps the pragma after each successful step.

Version 0 -> 1: base tables (documents, chunks, FTS, taxonomy, evidence, …)
Version 1 -> 2: V3 schema (routes, bridges, steps, packs, tags, archetypes, …)
Version 2 -> 3: V3.1 (quote_pack_items)
Version 3 -> 4: quotes classification columns
Version 4 -> 5: cases taxonomy columns + section_title on chunks + evidence weight
Version 8 -> 9: document revisions + active revision pointers
Version 10 -> 11: structured knowledge + canonical concepts
"""
from __future__ import annotations

from library.db import connect


# -- individual migration functions ----------------------------------------

_BASE_SQL = '''
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_pdf TEXT UNIQUE,
  text_path TEXT,
  status TEXT
);
CREATE TABLE IF NOT EXISTS document_chunks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id INTEGER NOT NULL,
  chunk_index INTEGER NOT NULL,
  content TEXT NOT NULL,
  char_count INTEGER NOT NULL,
  FOREIGN KEY(document_id) REFERENCES documents(id)
);
CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts USING fts5(content, content='document_chunks', content_rowid='id');
CREATE TABLE IF NOT EXISTS themes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  theme_name TEXT UNIQUE,
  description TEXT
);
CREATE TABLE IF NOT EXISTS principles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  principle_name TEXT UNIQUE,
  description TEXT
);
CREATE TABLE IF NOT EXISTS patterns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pattern_name TEXT UNIQUE,
  description TEXT
);
CREATE TABLE IF NOT EXISTS intervention_styles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  style_name TEXT UNIQUE,
  description TEXT
);
CREATE TABLE IF NOT EXISTS quotes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id INTEGER,
  chunk_id INTEGER,
  quote_text TEXT,
  note TEXT,
  quote_type TEXT,
  theme_name TEXT,
  principle_name TEXT,
  pattern_name TEXT,
  FOREIGN KEY(document_id) REFERENCES documents(id),
  FOREIGN KEY(chunk_id) REFERENCES document_chunks(id)
);
CREATE TABLE IF NOT EXISTS cases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_name TEXT UNIQUE,
  description TEXT,
  intervention_style TEXT,
  risk_note TEXT
);
CREATE TABLE IF NOT EXISTS argument_frames (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  frame_name TEXT UNIQUE,
  description TEXT
);
CREATE TABLE IF NOT EXISTS relationship_patterns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pattern_name TEXT UNIQUE,
  description TEXT
);
CREATE TABLE IF NOT EXISTS developmental_problems (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  problem_name TEXT UNIQUE,
  description TEXT
);
CREATE TABLE IF NOT EXISTS symbolic_motifs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  motif_name TEXT UNIQUE,
  description TEXT
);
CREATE TABLE IF NOT EXISTS intervention_examples (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  example_name TEXT UNIQUE,
  description TEXT
);
CREATE TABLE IF NOT EXISTS theme_evidence (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  theme_id INTEGER,
  chunk_id INTEGER,
  note TEXT,
  FOREIGN KEY(theme_id) REFERENCES themes(id),
  FOREIGN KEY(chunk_id) REFERENCES document_chunks(id)
);
CREATE TABLE IF NOT EXISTS principle_evidence (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  principle_id INTEGER,
  chunk_id INTEGER,
  note TEXT,
  FOREIGN KEY(principle_id) REFERENCES principles(id),
  FOREIGN KEY(chunk_id) REFERENCES document_chunks(id)
);
CREATE TABLE IF NOT EXISTS pattern_evidence (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pattern_id INTEGER,
  chunk_id INTEGER,
  note TEXT,
  FOREIGN KEY(pattern_id) REFERENCES patterns(id),
  FOREIGN KEY(chunk_id) REFERENCES document_chunks(id)
);
'''

_V3_SQL = '''
CREATE TABLE IF NOT EXISTS source_route_strength (
  id INTEGER PRIMARY KEY,
  source_name TEXT NOT NULL,
  route_name TEXT NOT NULL,
  strength INTEGER DEFAULT 0,
  note TEXT,
  UNIQUE(source_name, route_name)
);

CREATE TABLE IF NOT EXISTS bridge_to_action_templates (
  id INTEGER PRIMARY KEY,
  template_name TEXT NOT NULL UNIQUE,
  used_for_theme TEXT,
  used_for_pattern TEXT,
  diagnosis_stub TEXT,
  responsibility_stub TEXT,
  next_step_stub TEXT,
  long_term_stub TEXT,
  tone_profile TEXT,
  note TEXT
);

CREATE TABLE IF NOT EXISTS next_step_library (
  id INTEGER PRIMARY KEY,
  step_name TEXT NOT NULL UNIQUE,
  used_for_theme TEXT,
  used_for_pattern TEXT,
  used_for_archetype TEXT,
  step_text TEXT,
  difficulty TEXT,
  time_horizon TEXT,
  contraindications TEXT,
  note TEXT
);

CREATE TABLE IF NOT EXISTS route_quote_packs (
  id INTEGER PRIMARY KEY,
  pack_name TEXT NOT NULL UNIQUE,
  route_name TEXT NOT NULL,
  preferred_sources TEXT,
  preferred_quote_types TEXT,
  note TEXT
);

CREATE TABLE IF NOT EXISTS confidence_tags (
  id INTEGER PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id INTEGER NOT NULL,
  confidence_level TEXT,
  curation_level TEXT,
  source_count INTEGER DEFAULT 0,
  manual_override INTEGER DEFAULT 0,
  note TEXT,
  UNIQUE(entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS archetype_interventions (
  archetype_name TEXT NOT NULL,
  intervention_pattern_name TEXT NOT NULL,
  note TEXT,
  PRIMARY KEY(archetype_name, intervention_pattern_name)
);

CREATE TABLE IF NOT EXISTS archetype_anti_patterns (
  archetype_name TEXT NOT NULL,
  anti_pattern_name TEXT NOT NULL,
  note TEXT,
  PRIMARY KEY(archetype_name, anti_pattern_name)
);

CREATE TABLE IF NOT EXISTS case_archetypes (
  case_id INTEGER NOT NULL,
  archetype_name TEXT NOT NULL,
  note TEXT,
  PRIMARY KEY(case_id, archetype_name)
);

CREATE TABLE IF NOT EXISTS case_interventions (
  case_id INTEGER NOT NULL,
  intervention_pattern_name TEXT NOT NULL,
  note TEXT,
  PRIMARY KEY(case_id, intervention_pattern_name)
);

CREATE TABLE IF NOT EXISTS motif_cases (
  motif_id INTEGER NOT NULL,
  case_id INTEGER NOT NULL,
  note TEXT,
  PRIMARY KEY(motif_id, case_id)
);

CREATE TABLE IF NOT EXISTS motif_interventions (
  motif_id INTEGER NOT NULL,
  intervention_pattern_name TEXT NOT NULL,
  note TEXT,
  PRIMARY KEY(motif_id, intervention_pattern_name)
);

CREATE TABLE IF NOT EXISTS pattern_next_steps (
  pattern_name TEXT NOT NULL,
  step_id INTEGER NOT NULL,
  note TEXT,
  PRIMARY KEY(pattern_name, step_id)
);

CREATE TABLE IF NOT EXISTS theme_next_steps (
  theme_name TEXT NOT NULL,
  step_id INTEGER NOT NULL,
  note TEXT,
  PRIMARY KEY(theme_name, step_id)
);

CREATE TABLE IF NOT EXISTS archetype_quote_packs (
  archetype_name TEXT NOT NULL,
  pack_id INTEGER NOT NULL,
  note TEXT,
  PRIMARY KEY(archetype_name, pack_id)
);
'''

_V31_SQL = '''
CREATE TABLE IF NOT EXISTS quote_pack_items (
  pack_id INTEGER NOT NULL,
  quote_id INTEGER NOT NULL,
  note TEXT,
  PRIMARY KEY(pack_id, quote_id)
);
'''


def _add_col(cur, table, col, spec):
    cols = [r[1] for r in cur.execute(f'PRAGMA table_info({table})').fetchall()]
    if col not in cols:
        cur.execute(f'ALTER TABLE {table} ADD COLUMN {col} {spec}')


def _migrate_base(conn):
    conn.cursor().executescript(_BASE_SQL)


def _migrate_v3(conn):
    conn.cursor().executescript(_V3_SQL)


def _migrate_v31(conn):
    conn.cursor().executescript(_V31_SQL)


def _migrate_quotes_v2(conn):
    cur = conn.cursor()
    _add_col(cur, 'quotes', 'quote_type', 'TEXT')
    _add_col(cur, 'quotes', 'theme_name', 'TEXT')
    _add_col(cur, 'quotes', 'principle_name', 'TEXT')
    _add_col(cur, 'quotes', 'pattern_name', 'TEXT')


def _migrate_v5_taxonomy_and_chunks(conn):
    """V5: Add taxonomy columns to cases, section_title to chunks, weight to evidence."""
    cur = conn.cursor()
    _add_col(cur, 'cases', 'theme_name', 'TEXT')
    _add_col(cur, 'cases', 'principle_name', 'TEXT')
    _add_col(cur, 'cases', 'pattern_name', 'TEXT')
    _add_col(cur, 'cases', 'source_document_id', 'INTEGER')
    _add_col(cur, 'document_chunks', 'section_title', 'TEXT')
    _add_col(cur, 'theme_evidence', 'weight', 'REAL DEFAULT 1.0')
    _add_col(cur, 'principle_evidence', 'weight', 'REAL DEFAULT 1.0')
    _add_col(cur, 'pattern_evidence', 'weight', 'REAL DEFAULT 1.0')


_V6_EMBEDDINGS_SQL = '''
CREATE TABLE IF NOT EXISTS chunk_embeddings (
    chunk_id INTEGER PRIMARY KEY,
    model_name TEXT NOT NULL,
    embedding BLOB NOT NULL,
    dimensions INTEGER NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(chunk_id) REFERENCES document_chunks(id)
);
CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_model ON chunk_embeddings(model_name);
'''


def _migrate_v6_embeddings(conn):
    """V6: Add chunk_embeddings table for hybrid retrieval."""
    conn.cursor().executescript(_V6_EMBEDDINGS_SQL)


def _migrate_v7_doc_mtime(conn):
    """Add text_mtime column to documents for incremental build detection."""
    cur = conn.cursor()
    cols = {row[1] for row in cur.execute('PRAGMA table_info(documents)').fetchall()}
    if 'text_mtime' not in cols:
        cur.execute('ALTER TABLE documents ADD COLUMN text_mtime REAL')
    conn.commit()


# -- ordered migration registry -------------------------------------------

def _migrate_v8_intervention_taxonomy(conn):
    """Add taxonomy columns to intervention_examples."""
    cur = conn.cursor()
    cols = {row[1] for row in cur.execute('PRAGMA table_info(intervention_examples)').fetchall()}
    for col in ('theme_name', 'principle_name', 'pattern_name'):
        if col not in cols:
            cur.execute(f'ALTER TABLE intervention_examples ADD COLUMN {col} TEXT')
    conn.commit()


def _migrate_v9_document_revisions(conn):
    """Add document revision tracking and map existing chunks into active revisions."""
    cur = conn.cursor()
    _add_col(cur, 'documents', 'active_revision_id', 'INTEGER')
    _add_col(cur, 'document_chunks', 'revision_id', 'INTEGER')

    cur.executescript(
        '''
        CREATE TABLE IF NOT EXISTS document_revisions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          document_id INTEGER NOT NULL,
          revision_number INTEGER NOT NULL,
          source_text_mtime REAL,
          status TEXT DEFAULT 'active',
          created_at TEXT DEFAULT (datetime('now')),
          UNIQUE(document_id, revision_number),
          FOREIGN KEY(document_id) REFERENCES documents(id)
        );
        CREATE INDEX IF NOT EXISTS idx_document_revisions_document
          ON document_revisions(document_id, revision_number);
        CREATE INDEX IF NOT EXISTS idx_document_chunks_revision
          ON document_chunks(revision_id, chunk_index);
        '''
    )

    docs = cur.execute('SELECT id, text_mtime, active_revision_id FROM documents').fetchall()
    for document_id, text_mtime, active_revision_id in docs:
        if active_revision_id:
            continue
        row = cur.execute(
            'SELECT revision_id FROM document_chunks '
            'WHERE document_id = ? AND revision_id IS NOT NULL '
            'ORDER BY revision_id DESC LIMIT 1',
            (document_id,),
        ).fetchone()
        if row and row[0]:
            cur.execute(
                'UPDATE documents SET active_revision_id = ? WHERE id = ?',
                (row[0], document_id),
            )
            continue

        has_chunks = cur.execute(
            'SELECT 1 FROM document_chunks WHERE document_id = ? LIMIT 1',
            (document_id,),
        ).fetchone()
        if not has_chunks:
            continue

        cur.execute(
            'INSERT INTO document_revisions (document_id, revision_number, source_text_mtime, status) '
            'VALUES (?, ?, ?, ?)',
            (document_id, 1, text_mtime, 'active'),
        )
        revision_id = cur.lastrowid
        cur.execute(
            'UPDATE document_chunks SET revision_id = ? '
            'WHERE document_id = ? AND revision_id IS NULL',
            (revision_id, document_id),
        )
        cur.execute(
            'UPDATE documents SET active_revision_id = ? WHERE id = ?',
            (revision_id, document_id),
        )
    conn.commit()


def _migrate_v10_intervention_source_doc(conn):
    """Add source_document_id to intervention_examples."""
    cur = conn.cursor()
    _add_col(cur, 'intervention_examples', 'source_document_id', 'INTEGER')
    conn.commit()


_V11_STRUCTURED_KNOWLEDGE_SQL = '''
CREATE TABLE IF NOT EXISTS canonical_concepts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  concept_slug TEXT NOT NULL UNIQUE,
  concept_name TEXT NOT NULL UNIQUE,
  description TEXT,
  theme_name TEXT,
  principle_name TEXT,
  pattern_name TEXT,
  priority INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS canonical_concept_aliases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  concept_id INTEGER NOT NULL,
  alias_text TEXT NOT NULL,
  UNIQUE(concept_id, alias_text),
  FOREIGN KEY(concept_id) REFERENCES canonical_concepts(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_canonical_concept_aliases_text
  ON canonical_concept_aliases(alias_text);

CREATE TABLE IF NOT EXISTS canonical_concept_sources (
  concept_id INTEGER NOT NULL,
  document_id INTEGER NOT NULL,
  support_type TEXT NOT NULL,
  support_ref TEXT NOT NULL DEFAULT '',
  note TEXT,
  PRIMARY KEY(concept_id, document_id, support_type, support_ref),
  FOREIGN KEY(concept_id) REFERENCES canonical_concepts(id) ON DELETE CASCADE,
  FOREIGN KEY(document_id) REFERENCES documents(id)
);
CREATE INDEX IF NOT EXISTS idx_canonical_concept_sources_document
  ON canonical_concept_sources(document_id, support_type);

CREATE TABLE IF NOT EXISTS definitions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  term_name TEXT NOT NULL UNIQUE,
  summary TEXT NOT NULL,
  theme_name TEXT,
  principle_name TEXT,
  pattern_name TEXT,
  source_document_id INTEGER,
  canonical_concept_id INTEGER,
  note TEXT,
  FOREIGN KEY(source_document_id) REFERENCES documents(id),
  FOREIGN KEY(canonical_concept_id) REFERENCES canonical_concepts(id)
);

CREATE TABLE IF NOT EXISTS claims (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  claim_text TEXT NOT NULL UNIQUE,
  summary TEXT,
  claim_kind TEXT,
  theme_name TEXT,
  principle_name TEXT,
  pattern_name TEXT,
  source_document_id INTEGER,
  canonical_concept_id INTEGER,
  note TEXT,
  FOREIGN KEY(source_document_id) REFERENCES documents(id),
  FOREIGN KEY(canonical_concept_id) REFERENCES canonical_concepts(id)
);

CREATE TABLE IF NOT EXISTS practices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  practice_name TEXT NOT NULL UNIQUE,
  summary TEXT NOT NULL,
  difficulty TEXT,
  time_horizon TEXT,
  theme_name TEXT,
  principle_name TEXT,
  pattern_name TEXT,
  source_document_id INTEGER,
  canonical_concept_id INTEGER,
  note TEXT,
  FOREIGN KEY(source_document_id) REFERENCES documents(id),
  FOREIGN KEY(canonical_concept_id) REFERENCES canonical_concepts(id)
);

CREATE TABLE IF NOT EXISTS objections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  objection_name TEXT NOT NULL UNIQUE,
  summary TEXT NOT NULL,
  response TEXT,
  theme_name TEXT,
  principle_name TEXT,
  pattern_name TEXT,
  source_document_id INTEGER,
  canonical_concept_id INTEGER,
  note TEXT,
  FOREIGN KEY(source_document_id) REFERENCES documents(id),
  FOREIGN KEY(canonical_concept_id) REFERENCES canonical_concepts(id)
);

CREATE TABLE IF NOT EXISTS chapter_summaries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id INTEGER NOT NULL,
  section_title TEXT NOT NULL,
  summary TEXT NOT NULL,
  theme_name TEXT,
  principle_name TEXT,
  pattern_name TEXT,
  canonical_concept_id INTEGER,
  note TEXT,
  UNIQUE(document_id, section_title),
  FOREIGN KEY(document_id) REFERENCES documents(id),
  FOREIGN KEY(canonical_concept_id) REFERENCES canonical_concepts(id)
);
CREATE INDEX IF NOT EXISTS idx_chapter_summaries_document
  ON chapter_summaries(document_id);
'''


def _migrate_v11_structured_knowledge(conn):
    """Add structured knowledge tables and canonical concept normalization."""
    conn.cursor().executescript(_V11_STRUCTURED_KNOWLEDGE_SQL)
    conn.commit()


MIGRATIONS: list[tuple[int, callable]] = [
    (1, _migrate_base),
    (2, _migrate_v3),
    (3, _migrate_v31),
    (4, _migrate_quotes_v2),
    (5, _migrate_v5_taxonomy_and_chunks),
    (6, _migrate_v6_embeddings),
    (7, _migrate_v7_doc_mtime),
    (8, _migrate_v8_intervention_taxonomy),
    (9, _migrate_v9_document_revisions),
    (10, _migrate_v10_intervention_source_doc),
    (11, _migrate_v11_structured_knowledge),
]

LATEST_VERSION = MIGRATIONS[-1][0]


def get_schema_version(conn) -> int:
    """Read current schema version from PRAGMA user_version."""
    return conn.execute('PRAGMA user_version').fetchone()[0]


def _set_schema_version(conn, version: int):
    conn.execute(f'PRAGMA user_version = {int(version)}')


def migrate_up(conn=None):
    """Apply all pending migrations.  Returns (old_version, new_version)."""
    owned = conn is None
    if owned:
        ctx = connect()
        conn = ctx.__enter__()
    try:
        current = get_schema_version(conn)
        if current >= LATEST_VERSION:
            return current, current

        for version, fn in MIGRATIONS:
            if version > current:
                fn(conn)
                _set_schema_version(conn, version)
                conn.commit()

        new = get_schema_version(conn)
        return current, new
    except Exception:
        if owned:
            import sys
            ctx.__exit__(*sys.exc_info())
        raise
    else:
        if owned:
            ctx.__exit__(None, None, None)


# -- legacy entry points (kept for CLI backward-compat) --------------------

def migrate_v3():
    """Apply V3 schema migration. Returns status string."""
    with connect() as conn:
        _migrate_v3(conn)
    return 'migrated_v3'


def migrate_v31():
    """Apply V3.1 schema migration (quote_pack_items). Returns status string."""
    with connect() as conn:
        _migrate_v31(conn)
    return 'migrated_v31'


def migrate_quotes_v2():
    """Add classification columns to quotes table. Returns status string."""
    with connect() as conn:
        _migrate_quotes_v2(conn)
    return 'ok'
