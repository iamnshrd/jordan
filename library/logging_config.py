"""Structured JSON logging configuration for the Jordan agent.

Call ``setup()`` once at startup.  Every log record produced by the
``jordan`` logger hierarchy is formatted as a single-line JSON object
with keys: ``ts``, ``level``, ``logger``, ``msg``, and any ``extra``
fields passed via ``log.info("...", extra={...})``.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

from library.config import RUNTIME_LOG

_STANDARD_RECORD_KEYS = frozenset({
    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
    'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
    'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
    'processName', 'process', 'message', 'asctime',
})


def _safe_value(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, dict)):
        return value
    return str(value)


class JsonFormatter(logging.Formatter):
    """Emit each log record as a compact JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            'ts': datetime.fromtimestamp(record.created, tz=timezone.utc)
                         .isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'msg': record.getMessage(),
        }
        for key, val in record.__dict__.items():
            if key in _STANDARD_RECORD_KEYS or key.startswith('_'):
                continue
            payload[key] = _safe_value(val)
        if record.exc_info and record.exc_info[1]:
            payload['exception'] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup(level: int = logging.INFO):
    """Configure the ``jordan`` root logger with JSON output to stderr + file."""
    root = logging.getLogger('jordan')
    if root.handlers:
        return
    formatter = JsonFormatter()

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    RUNTIME_LOG.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(RUNTIME_LOG, encoding='utf-8')
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    root.setLevel(level)
