#!/usr/bin/env python3
"""Shared utility functions used across multiple modules."""
from __future__ import annotations

import json
import logging
import time
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

log = logging.getLogger('jordan')


# -- timing / observability ------------------------------------------------

_timing_ctx: threading.local = threading.local()
_trace_ctx: threading.local = threading.local()


@contextmanager
def timing_context():
    """Context manager that collects ``@timed`` measurements.

    Usage::

        with timing_context() as timings:
            result = orchestrate(question)
        print(timings)   # {'retrieve': 12.3, 'synthesize': 8.1, ...}
    """
    prev = getattr(_timing_ctx, 'timings', None)
    _timing_ctx.timings = {}
    try:
        yield _timing_ctx.timings
    finally:
        _timing_ctx.timings = prev


def _record_timing(stage: str, elapsed_ms: float):
    timings = getattr(_timing_ctx, 'timings', None)
    if timings is not None:
        timings[stage] = round(elapsed_ms, 2)


def _current_trace() -> dict | None:
    return getattr(_trace_ctx, 'value', None)


def _set_current_trace(value: dict | None) -> None:
    _trace_ctx.value = value


def current_trace_id() -> str:
    trace = _current_trace() or {}
    return trace.get('trace_id', '')


def current_trace_meta() -> dict:
    trace = _current_trace() or {}
    meta = {}
    for key in (
        'trace_id', 'span_id', 'parent_span_id', 'user_id',
        'purpose', 'question_preview',
    ):
        value = trace.get(key)
        if value:
            meta[key] = value
    return meta


def _question_preview(question: str, limit: int = 180) -> str:
    text = ' '.join((question or '').split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + '...'


def _generate_trace_id() -> str:
    return 'tr-' + uuid.uuid4().hex[:16]


def _generate_span_id() -> str:
    return 'sp-' + uuid.uuid4().hex[:12]


def _persist_trace_event(event: dict, *, store=None, user_id: str | None = None) -> None:
    if store is None or not user_id:
        return
    try:
        from library._core.state_store import KEY_TRACE_EVENTS
        store.append_jsonl(user_id, KEY_TRACE_EVENTS, event)
    except Exception:
        log.exception('Failed to persist trace event', extra={'event': 'trace.persist_failed'})


def _append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')


def persist_conversation_audit(event: dict) -> None:
    try:
        from library.config import CONVERSATION_AUDIT_LOG
        _append_jsonl(CONVERSATION_AUDIT_LOG, event)
    except Exception:
        log.exception(
            'Failed to persist conversation audit event',
            extra={'event': 'conversation.audit.persist_failed'},
        )


def audit_event(event: str, level: int = logging.INFO, **fields) -> dict:
    payload = {
        'event': event,
        'timestamp': now_iso(),
        **current_trace_meta(),
        **fields,
    }
    persist_conversation_audit(payload)
    log.log(level, event, extra=payload)
    return payload


def log_event(event: str, level: int = logging.INFO, *,
              store=None, user_id: str | None = None, **fields) -> dict:
    trace = _current_trace() or {}
    payload = {
        'event': event,
        'timestamp': now_iso(),
        **current_trace_meta(),
        **fields,
    }
    effective_store = store or trace.get('store')
    effective_user = user_id or trace.get('user_id')
    _persist_trace_event(payload, store=effective_store, user_id=effective_user)
    log.log(level, event, extra=payload)
    return payload


@contextmanager
def ensure_trace_context(*, user_id: str = 'default', store=None,
                         purpose: str = 'runtime', question: str = '',
                         trace_id: str | None = None):
    existing = _current_trace()
    if existing is not None:
        yield existing
        return

    trace = {
        'trace_id': trace_id or _generate_trace_id(),
        'span_id': '',
        'parent_span_id': '',
        'user_id': user_id,
        'purpose': purpose,
        'question_preview': _question_preview(question),
        'store': store,
    }
    _set_current_trace(trace)
    try:
        log_event(
            'trace.started',
            store=store,
            user_id=user_id,
            question_preview=trace['question_preview'],
            purpose=purpose,
        )
        yield trace
    finally:
        log_event('trace.finished', store=store, user_id=user_id)
        _set_current_trace(None)


@contextmanager
def traced_stage(stage: str, *, store=None, user_id: str | None = None, **fields):
    trace = _current_trace() or {}
    prev_span = trace.get('span_id', '')
    span_id = _generate_span_id()
    if trace:
        trace['parent_span_id'] = prev_span
        trace['span_id'] = span_id
    started = time.monotonic()
    log_event(
        'stage.started',
        level=logging.DEBUG,
        store=store,
        user_id=user_id,
        stage=stage,
        span_id=span_id,
        parent_span_id=prev_span or '',
        **fields,
    )
    try:
        yield span_id
    except Exception as exc:
        elapsed_ms = round((time.monotonic() - started) * 1000, 2)
        log_event(
            'stage.failed',
            level=logging.ERROR,
            store=store,
            user_id=user_id,
            stage=stage,
            span_id=span_id,
            parent_span_id=prev_span or '',
            elapsed_ms=elapsed_ms,
            error=str(exc),
            **fields,
        )
        raise
    else:
        elapsed_ms = round((time.monotonic() - started) * 1000, 2)
        log_event(
            'stage.finished',
            level=logging.DEBUG,
            store=store,
            user_id=user_id,
            stage=stage,
            span_id=span_id,
            parent_span_id=prev_span or '',
            elapsed_ms=elapsed_ms,
            **fields,
        )
    finally:
        if trace:
            trace['span_id'] = prev_span
            trace['parent_span_id'] = ''


def timed(stage: str):
    """Decorator that logs and records execution time for *stage*."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            t0 = time.monotonic()
            try:
                return fn(*args, **kwargs)
            finally:
                elapsed_ms = (time.monotonic() - t0) * 1000
                _record_timing(stage, elapsed_ms)
                log.debug('%s completed in %.1f ms', stage,
                          elapsed_ms,
                          extra={
                              'stage': stage,
                              'elapsed_ms': round(elapsed_ms, 2),
                              **current_trace_meta(),
                          })
        return wrapper
    return decorator


def now_iso():
    """Return current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default=None):
    """Read and parse a JSON file, returning *default* if it is missing or broken.

    If the file contains JSON ``null``, *default* is returned as well.
    """
    p = Path(path)
    if not p.exists():
        return default if default is not None else {}
    try:
        result = json.loads(p.read_text(encoding='utf-8'))
        if result is None:
            return default if default is not None else {}
        return result
    except (json.JSONDecodeError, OSError) as exc:
        log.warning('Failed to load %s: %s', path, exc)
        return default if default is not None else {}


def save_json(path, data, ensure_ascii=False, indent=2):
    """Atomically write *data* as pretty-printed JSON via tmp+rename."""
    import os, tempfile
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(target.parent), suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
        os.replace(tmp, str(target))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_checkpoints(path):
    """Read a JSONL checkpoint file into a list of dicts."""
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


SYNONYM_MAP: dict[str, list[str]] = {
    'смысл': ['meaning', 'purpose', 'направление', 'цель'],
    'meaning': ['смысл', 'purpose', 'направление'],
    'purpose': ['смысл', 'meaning', 'цель'],
    'direction': ['направление', 'цель', 'путь'],
    'направление': ['direction', 'цель', 'путь', 'смысл'],
    'цель': ['direction', 'purpose', 'направление', 'смысл'],
    'resentment': ['обида', 'горечь', 'злость'],
    'обида': ['resentment', 'горечь', 'злость'],
    'горечь': ['resentment', 'обида'],
    'злость': ['resentment', 'обида'],
    'truth': ['правда', 'честность', 'ложь'],
    'правда': ['truth', 'честность'],
    'ложь': ['lie', 'самообман', 'truth'],
    'lie': ['ложь', 'самообман'],
    'самообман': ['self-deception', 'ложь'],
    'suffering': ['страдание', 'боль'],
    'страдание': ['suffering', 'боль'],
    'боль': ['pain', 'suffering', 'страдание'],
    'pain': ['боль', 'suffering'],
    'chaos': ['хаос', 'беспорядок'],
    'хаос': ['chaos', 'беспорядок'],
    'order': ['порядок', 'структура', 'дисциплина'],
    'порядок': ['order', 'структура', 'дисциплина'],
    'responsibility': ['ответственность', 'burden', 'бремя'],
    'ответственность': ['responsibility', 'burden', 'бремя', 'долг'],
    'стыд': ['shame', 'позор'],
    'shame': ['стыд', 'позор'],
    'избегание': ['avoidance', 'прокрастинация', 'откладывание'],
    'avoidance': ['избегание', 'прокрастинация'],
    'отношения': ['relationship', 'конфликт', 'партнер'],
    'relationship': ['отношения'],
    'карьера': ['career', 'vocation', 'призвание', 'работа'],
    'career': ['карьера', 'призвание'],
    'vocation': ['призвание', 'карьера'],
}


def fts_query(text, expand_synonyms=True):
    """Build an OR-based FTS5 query with optional synonym expansion."""
    max_tokens = get_threshold('fts_query_max_tokens', 8)
    max_tokens_long = get_threshold('fts_query_max_tokens_long', 16)
    words = [
        w
        for w in ''.join(
            ch if ch.isalnum() or ch.isspace() else ' ' for ch in text.lower()
        ).split()
        if len(w) >= 3
    ]
    if not words:
        return ''

    if expand_synonyms:
        expanded = set(words[:max_tokens])
        for w in words[:max_tokens]:
            for syn in SYNONYM_MAP.get(w, []):
                if len(syn) >= 3:
                    expanded.add(syn)
            for stem, syns in SYNONYM_MAP.items():
                if stem.startswith(w) or w.startswith(stem):
                    expanded.add(stem)
                    for syn in syns[:2]:
                        if len(syn) >= 3:
                            expanded.add(syn)
        words = list(expanded)[:max_tokens_long]

    return ' OR '.join(words) if words else ''


_thresholds_cache: dict | None = None


def get_threshold(key: str, default=None):
    """Read a named threshold from thresholds.json (cached)."""
    global _thresholds_cache
    if _thresholds_cache is None:
        from library.config import THRESHOLDS
        raw = load_json(THRESHOLDS, default={})
        _thresholds_cache = raw if isinstance(raw, dict) else {}
    return _thresholds_cache.get(key, default)


def slugify(name):
    """Produce a filesystem-safe slug from *name*."""
    out = []
    for ch in name.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in (' ', '-', '_', '.'):
            out.append('-')
    slug = ''.join(out)
    while '--' in slug:
        slug = slug.replace('--', '-')
    return slug.strip('-')
