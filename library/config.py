#!/usr/bin/env python3
"""Centralised paths and settings for the Jordan Peterson agent.

Every module imports paths from here instead of hardcoding them.
All paths are derived relative to this file so the project works
regardless of where it is deployed.
"""
from __future__ import annotations

from pathlib import Path
import json
import os
import re

ROOT = Path(__file__).resolve().parent            # library/
PROJECT = ROOT.parent                             # jordan/
WORKSPACE = PROJECT / 'workspace'
LOGS_DIR = WORKSPACE / 'logs'
VENDOR = PROJECT / '.vendor'

_runtime_log_override = (os.environ.get('JORDAN_LOG_PATH') or '').strip()
RUNTIME_LOG = (
    Path(_runtime_log_override).expanduser()
    if _runtime_log_override
    else LOGS_DIR / 'jordan.jsonl'
)

_conversation_audit_override = (
    os.environ.get('JORDAN_CONVERSATION_AUDIT_LOG') or ''
).strip()
CONVERSATION_AUDIT_LOG = (
    Path(_conversation_audit_override).expanduser()
    if _conversation_audit_override
    else LOGS_DIR / 'conversation_audit.jsonl'
)

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
ARTICLE_CONCEPTS = ROOT / 'article_concepts_manual.json'
ARTICLE_KNOWLEDGE = ROOT / 'article_knowledge_manual.json'
CANONICAL_CONCEPTS = ROOT / 'canonical_concepts_manual.json'
MANUAL_QUOTES = ROOT / 'manual_quotes.json'
MANUAL_QUOTES_BEYOND = ROOT / 'manual_quotes_beyond_order.json'
MANUAL_QUOTES_MAPS = ROOT / 'manual_quotes_maps_of_meaning.json'

# --- Intermediate build artefacts ---
KB_CANDIDATES = ROOT / 'kb_candidates.json'
KB_CANDIDATES_NORM = ROOT / 'kb_candidates_normalized.json'
QUOTES_CANDIDATES = ROOT / 'quotes_candidates.json'
QUOTES_NORMALIZED = ROOT / 'quotes_normalized.json'
INGEST_REPORT = ROOT / 'ingest_report.json'

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
VOICE_EXCERPT_CANDIDATES = ROOT / 'voice_excerpt_candidates.json'
CLARIFY_VOICE_PATTERNS = ROOT / 'clarify_voice_patterns.json'

# --- Document source hints (document_id -> friendly name) ---
_DOC_SOURCE_HINTS_STATIC = {
    1: '12-rules',
    2: 'maps-of-meaning',
    3: 'beyond-order',
}
_doc_source_hints_cache: dict | None = None
_doc_source_hints_cache_key: tuple[float | None, int, float | None] | None = None


def _simplify_source_key(value: str) -> str:
    """Collapse punctuation and spacing so source matching is stable."""
    return re.sub(r'[^a-zа-я0-9]+', ' ', (value or '').lower()).strip()


def friendly_source_name(source_pdf: str | None) -> str:
    """Return a stable logical source name for a document path."""
    source_pdf = (source_pdf or '').strip()
    lower = source_pdf.lower()
    simple = _simplify_source_key(source_pdf)
    if not lower:
        return ''
    if '12-pravil' in lower or '12-rules' in lower:
        return '12-rules'
    if 'maps-of-meaning' in lower:
        return 'maps-of-meaning'
    if 'beyond-order' in lower:
        return 'beyond-order'
    if (
        'что сделает тебя успешным' in lower
        or 'what-will-make-you-successful' in lower
        or 'what will make you successful' in simple
    ):
        return 'success-lecture'
    if (
        'between-order-and-chaos' in lower
        or 'between order and chaos' in simple
    ):
        return 'academy-between-order-chaos'
    if 'the-walled-garden' in lower or 'the walled garden' in simple:
        return 'academy-walled-garden'
    if 'desire-and-discipline' in lower or 'desire and discipline' in simple:
        return 'academy-desire-discipline'
    if 'fear-as-a-catalyst' in lower or 'fear as a catalyst' in simple:
        return 'academy-fear-catalyst'
    if 'faith-in-tragedy' in lower or 'faith in tragedy' in simple:
        return 'academy-faith-tragedy'
    if 'a-higher-vision' in lower or 'a higher vision' in simple:
        return 'academy-higher-vision'
    return source_pdf.rsplit('.', 1)[0].rsplit('/', 1)[-1]


def _doc_source_hints_fingerprint() -> tuple[float | None, int, float | None]:
    """Return a cheap fingerprint for cache invalidation.

    Includes DB mtime/size plus manifest mtime so long-running processes
    automatically refresh cached source hints after KB rebuilds or manifest edits.
    """
    try:
        db_stat = DB_PATH.stat()
        db_mtime = db_stat.st_mtime
        db_size = db_stat.st_size
    except OSError:
        db_mtime = None
        db_size = 0
    try:
        manifest_mtime = MANIFEST.stat().st_mtime
    except OSError:
        manifest_mtime = None
    return (db_mtime, db_size, manifest_mtime)


def get_doc_source_hints() -> dict:
    """Build source hints from DB with static fallback."""
    global _doc_source_hints_cache, _doc_source_hints_cache_key
    cache_key = _doc_source_hints_fingerprint()
    if (
        _doc_source_hints_cache is not None
        and _doc_source_hints_cache_key == cache_key
    ):
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
                    name = friendly_source_name(source_pdf)
                    hints[doc_id] = name
        _doc_source_hints_cache = hints
        _doc_source_hints_cache_key = cache_key
    except Exception:
        _doc_source_hints_cache = dict(_DOC_SOURCE_HINTS_STATIC)
        _doc_source_hints_cache_key = cache_key
    return _doc_source_hints_cache


def invalidate_doc_source_hints_cache() -> None:
    """Clear cached document source hints after KB document changes."""
    global _doc_source_hints_cache, _doc_source_hints_cache_key
    _doc_source_hints_cache = None
    _doc_source_hints_cache_key = None


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


def canonical_user_id(raw: str | None = None, *, channel: str = 'telegram') -> str:
    value = (raw or '').strip()
    if not value or value == 'default':
        return 'default'
    if value.startswith('agent:main:telegram:direct:'):
        return f"telegram:{value.rsplit(':', 1)[-1]}"
    if value.startswith('telegram:'):
        return value
    if value.isdigit():
        return f'{channel}:{value}'
    return value


def resolve_jordan_model_ref() -> str:
    """Return Jordan's configured provider/model ref.

    Prefer the active OpenClaw profile/agent model first so renderer/model
    paths stay aligned with the actual Jordan runtime selection. Keep
    Jordan-local env vars only as a manual fallback/override escape hatch when
    no active agent model is configured.
    """
    try:
        from library._core.runtime.openclaw_gateway_renderer import _load_openclaw_config
        from library._core.runtime.openclaw_gateway_renderer import _get_nested

        cfg = _load_openclaw_config()
        primary = _get_nested(cfg, ('agents', 'defaults', 'model', 'primary'))
        if isinstance(primary, str) and primary.strip():
            return primary.strip()
    except Exception:
        pass
    for env_key in ('JORDAN_MODEL_REF', 'JORDAN_MODEL'):
        raw = (os.environ.get(env_key) or '').strip()
        if raw:
            return raw
    return ''


def tracked_mentor_users_path() -> Path:
    return WORKSPACE / 'mentor_targets.json'


def load_tracked_mentor_users() -> dict:
    path = tracked_mentor_users_path()
    if not path.exists():
        return {'users': []}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {'users': []}
    if not isinstance(data, dict):
        return {'users': []}
    users = data.get('users')
    if not isinstance(users, list):
        data['users'] = []
    return data


def save_tracked_mentor_users(data: dict) -> None:
    path = tracked_mentor_users_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
