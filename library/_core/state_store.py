"""StateStore protocol and helpers for multi-tenant session state."""
from __future__ import annotations

import json
from typing import Protocol, runtime_checkable


@runtime_checkable
class StateStore(Protocol):
    """Abstract interface for per-user JSON state persistence."""

    def get_json(self, user_id: str, key: str,
                 default: dict | None = None) -> dict: ...

    def put_json(self, user_id: str, key: str, value: dict) -> None: ...

    def update_json(self, user_id: str, key: str,
                    mutator, default: dict | None = None) -> dict: ...

    def append_jsonl(self, user_id: str, key: str, event: dict) -> None: ...

    def read_jsonl(self, user_id: str, key: str) -> list[dict]: ...


# Well-known state keys (match former config constants)
KEY_CONTINUITY = 'continuity'
KEY_SESSION_STATE = 'session_state'
KEY_USER_STATE = 'user_state'
KEY_EFFECTIVENESS = 'effectiveness_memory'
KEY_CHECKPOINTS = 'session_checkpoints'
KEY_PROGRESS_STATE = 'progress_state'
KEY_CONTEXT_GRAPH = 'context_graph'
KEY_CONTINUITY_SUMMARY = 'continuity_summary'
KEY_REACTION_ESTIMATE = 'user_reaction_estimate'
KEY_DIALOGUE_STATE = 'dialogue_state'
KEY_MENTOR_STATE = 'mentor_state'
KEY_MENTOR_EVENTS = 'mentor_events'
KEY_MENTOR_DELAYS = 'mentor_delays'
KEY_COMMITMENTS = 'commitments'
KEY_TRACE_EVENTS = 'trace_events'
