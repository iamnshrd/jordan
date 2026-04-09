#!/usr/bin/env python3
"""Schema migrations for the knowledge base."""
from library.config import DB_PATH
from library.db import connect

# ── V3 schema DDL ────────────────────────────────────────────────────────────

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


def migrate_v3():
    """Apply V3 schema migration. Returns status string."""
    with connect() as conn:
        cur = conn.cursor()
        cur.executescript(_V3_SQL)
    return 'migrated_v3'


def migrate_v31():
    """Apply V3.1 schema migration (quote_pack_items). Returns status string."""
    with connect() as conn:
        cur = conn.cursor()
        cur.executescript(_V31_SQL)
    return 'migrated_v31'


def migrate_quotes_v2():
    """Add classification columns to quotes table. Returns status string."""
    with connect() as conn:
        cur = conn.cursor()
        _add_col(cur, 'quotes', 'quote_type', 'TEXT')
        _add_col(cur, 'quotes', 'theme_name', 'TEXT')
        _add_col(cur, 'quotes', 'principle_name', 'TEXT')
        _add_col(cur, 'quotes', 'pattern_name', 'TEXT')
    return 'ok'
