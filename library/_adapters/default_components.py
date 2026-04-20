"""Default adapter implementations wrapping the controlled runtime pipeline.

The canonical public interface is ``AgentRuntime``. The thin wrappers below are
kept only for internal diagnostics and compatibility; they now delegate through
the controlled plan builder instead of calling legacy stages independently.
"""
from __future__ import annotations

from library._core.state_store import StateStore


class DefaultFrameSelector:
    """Legacy diagnostic wrapper exposing the selected frame from a safe plan."""

    def __init__(self, store: StateStore | None = None):
        self._store = store

    def select(self, question: str, user_id: str = 'default') -> dict:
        from library._core.runtime.planner import build_answer_plan
        plan = build_answer_plan(question, user_id=user_id,
                                 store=self._store, purpose='prompt')
        return plan.selection


class DefaultSynthesizer:
    """Legacy diagnostic wrapper exposing synthesis from a safe plan."""

    def __init__(self, store: StateStore | None = None):
        self._store = store

    def synthesize(self, question: str, user_id: str = 'default') -> dict:
        from library._core.runtime.planner import build_answer_plan
        plan = build_answer_plan(question, user_id=user_id,
                                 store=self._store, purpose='prompt')
        return plan.synthesis or {}


class DefaultRenderer:
    """Legacy renderer; direct rendering is internal-only."""

    def render(self, data: dict, continuity: dict,
               mode: str = 'deep', voice: str = 'default') -> str:
        raise RuntimeError(
            'Direct rendering is internal-only; use AgentRuntime.handle() '
            'or respond() through the controlled runtime pipeline.'
        )


def create_default_runtime(store: StateStore | None = None):
    """Assemble an ``AgentRuntime`` wired with the default store."""
    from library.config import get_default_store
    from library._core.runtime.agent import AgentRuntime

    store = store or get_default_store()
    return AgentRuntime(store=store)
