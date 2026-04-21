"""AgentRuntime -- thin wrapper that delegates to the unified orchestration pipeline.

All reasoning goes through ``orchestrate()`` / ``orchestrate_for_llm()``
to ensure consistent quality gates, validation, and caching.
"""
from __future__ import annotations

from library._core.state_store import StateStore
from library._core.runtime.orchestrator import (
    orchestrate, orchestrate_diagnostics, orchestrate_for_adapter, orchestrate_for_llm,
    detect_mode, should_use_kb,
)


class AgentRuntime:
    """Runtime assembled from a StateStore.

    ``handle()`` delegates to the shared orchestrator pipeline.
    """

    def __init__(self, store: StateStore):
        self.store = store

    @staticmethod
    def detect_mode(question: str) -> str:
        return detect_mode(question)

    @staticmethod
    def should_use_kb(question: str) -> bool:
        return should_use_kb(question)

    def handle(self, question: str, user_id: str = 'default') -> dict:
        return orchestrate(question, user_id=user_id, store=self.store)

    def handle_for_llm(self, question: str, user_id: str = 'default') -> dict:
        return orchestrate_for_llm(question, user_id=user_id, store=self.store)

    def handle_for_adapter(self, question: str, user_id: str = 'default') -> dict:
        return orchestrate_for_adapter(question, user_id=user_id, store=self.store)

    def inspect(self, question: str, user_id: str = 'default',
                purpose: str = 'prompt') -> dict:
        return orchestrate_diagnostics(
            question, user_id=user_id, store=self.store, purpose=purpose,
        )
