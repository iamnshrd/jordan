#!/usr/bin/env python3
"""Centralised paths and settings for the Jordan Peterson agent.

Every module imports paths from here instead of hardcoding them.
All paths are derived relative to this file so the project works
regardless of where it is deployed.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent            # library/
PROJECT = ROOT.parent                             # jordan/
WORKSPACE = PROJECT / 'workspace'

# --- SQLite knowledge base ---
DB_PATH = ROOT / 'jordan_knowledge.db'

# --- Manifest & source material ---
MANIFEST = ROOT / 'manifest.json'
INCOMING = ROOT / 'incoming'
BOOKS = ROOT / 'books'
ARTICLES = ROOT / 'articles'
TEXTS = ROOT / 'texts'

# --- Library JSON assets ---
VOICE_MODES = ROOT / 'voice_modes.json'
SOURCE_ARBITRATION = ROOT / 'source_arbitration_rules.json'
QUESTION_ARCHETYPES = ROOT / 'question_archetypes.json'
INTERVENTION_PATTERNS = ROOT / 'intervention_patterns.json'
SOURCE_ROLE_PROFILES = ROOT / 'source_role_profiles.json'
SOURCE_BLEND_EXAMPLES = ROOT / 'source_blend_examples.json'
BEYOND_ORDER_CONCEPTS = ROOT / 'beyond_order_concepts.json'
MAPS_OF_MEANING_CONCEPTS = ROOT / 'maps_of_meaning_concepts.json'
TWELVE_RULES_CONCEPTS = ROOT / 'twelve_rules_concepts.json'
MANUAL_QUOTES = ROOT / 'manual_quotes.json'
MANUAL_QUOTES_BEYOND = ROOT / 'manual_quotes_beyond_order.json'
MANUAL_QUOTES_MAPS = ROOT / 'manual_quotes_maps_of_meaning.json'

# --- Intermediate build artefacts ---
KB_CANDIDATES = ROOT / 'kb_candidates.json'
KB_CANDIDATES_NORM = ROOT / 'kb_candidates_normalized.json'
QUOTES_CANDIDATES = ROOT / 'quotes_candidates.json'
QUOTES_NORMALIZED = ROOT / 'quotes_normalized.json'
INGEST_REPORT = ROOT / 'ingest_report.json'

# --- Workspace JSON state files (legacy, kept for backward-compat) ---
CONTINUITY = WORKSPACE / 'continuity.json'
SESSION_STATE = WORKSPACE / 'session_state.json'
USER_STATE = WORKSPACE / 'user_state.json'
EFFECTIVENESS = WORKSPACE / 'effectiveness_memory.json'
CHECKPOINTS = WORKSPACE / 'session_checkpoints.jsonl'
PROGRESS_STATE = WORKSPACE / 'progress_state.json'
CONTEXT_GRAPH = WORKSPACE / 'context_graph.json'
CONTINUITY_SUMMARY = WORKSPACE / 'continuity_summary.json'
REACTION_ESTIMATE = WORKSPACE / 'user_reaction_estimate.json'

# --- Runtime thresholds (tunable) ---
THRESHOLDS = ROOT / 'thresholds.json'

# --- Eval / regression artefacts ---
EVAL_CASES = ROOT / 'eval_cases.json'
EVAL_REPORT = ROOT / 'eval_report.json'
RUNTIME_REGRESSION_CASES = ROOT / 'runtime_regression_cases.json'
RUNTIME_REGRESSION_REPORT = ROOT / 'runtime_regression_report.json'
VOICE_REGRESSION_CASES = ROOT / 'voice_regression_cases.json'
VOICE_REGRESSION_REPORT = ROOT / 'voice_regression_report.json'
RUNTIME_AUDIT_REPORT = ROOT / 'runtime_audit_report.json'

# --- Document source hints (document_id -> friendly name) ---
_DOC_SOURCE_HINTS_STATIC = {
    1: '12-rules',
    2: 'maps-of-meaning',
    3: 'beyond-order',
}
_doc_source_hints_cache: dict | None = None


def get_doc_source_hints() -> dict:
    """Build source hints from DB with static fallback."""
    global _doc_source_hints_cache
    if _doc_source_hints_cache is not None:
        return _doc_source_hints_cache
    try:
        from library.db import connect
        hints = dict(_DOC_SOURCE_HINTS_STATIC)
        with connect(auto_migrate=False) as conn:
            cur = conn.cursor()
            for row in cur.execute(
                'SELECT id, source_pdf FROM documents'
            ).fetchall():
                doc_id, source_pdf = row
                if doc_id not in hints and source_pdf:
                    name = source_pdf.rsplit('.', 1)[0].rsplit('/', 1)[-1]
                    hints[doc_id] = name
        _doc_source_hints_cache = hints
    except Exception:
        _doc_source_hints_cache = dict(_DOC_SOURCE_HINTS_STATIC)
    return _doc_source_hints_cache


# --- Common stop snippets (shared by normalize + quotes pipelines) ---
COMMON_STOP_SNIPPETS = [
    'isbn', 'удк', 'ббк', 'оглавление', 'предисловие', 'вступление',
    'table of contents', 'copyright', 'random house', 'footnote', 'see also',
]


# --- Multi-tenant store factory ---

_default_store = None


def get_default_store():
    """Return a singleton FileSystemStore rooted at WORKSPACE."""
    global _default_store
    if _default_store is None:
        from library._adapters.fs_store import FileSystemStore
        _default_store = FileSystemStore(WORKSPACE)
    return _default_store
