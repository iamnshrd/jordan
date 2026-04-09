"""Session checkpoint logging.

Refactored from: log_session_checkpoint.
"""
import json

from library.config import CHECKPOINTS
from library.utils import now_iso


def log(payload):
    """Append a checkpoint entry to the JSONL log.

    Returns the payload dict with the injected timestamp.
    """
    payload['timestamp'] = now_iso()
    with open(CHECKPOINTS, 'a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')
    return payload
