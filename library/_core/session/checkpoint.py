"""Session checkpoint logging.

Refactored from: log_session_checkpoint.
"""
from __future__ import annotations

from library.config import get_default_store
from library._core.state_store import StateStore, KEY_CHECKPOINTS
from library.utils import now_iso


def log(payload, user_id: str = 'default',
        store: StateStore | None = None):
    """Append a checkpoint entry to the JSONL log.

    Returns the payload dict with the injected timestamp.
    """
    store = store or get_default_store()
    payload['timestamp'] = now_iso()
    store.append_jsonl(user_id, KEY_CHECKPOINTS, payload)
    return payload
