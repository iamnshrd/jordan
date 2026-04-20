"""Session checkpoint logging.

Refactored from: log_session_checkpoint.
"""
from __future__ import annotations

from library.config import canonical_user_id, get_default_store
from library._core.state_store import StateStore, KEY_CHECKPOINTS
from library.utils import current_trace_meta, now_iso


def log(payload, user_id: str = 'default',
        store: StateStore | None = None):
    """Append a checkpoint entry to the JSONL log.

    Returns a *copy* of the payload dict with the injected timestamp.
    The original ``payload`` is not mutated.
    """
    user_id = canonical_user_id(user_id)
    store = store or get_default_store()
    entry = {**payload, **current_trace_meta(), 'timestamp': now_iso()}
    store.append_jsonl(user_id, KEY_CHECKPOINTS, entry)
    return entry
