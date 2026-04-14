"""Default adapter implementations wrapping existing modules.

These thin wrappers satisfy the protocol contracts defined in
``library._core.protocols`` by delegating to the existing procedural code.
"""
from __future__ import annotations

from library._core.state_store import StateStore


class DefaultFrameSelector:
    """Wraps ``frame.select_frame()``."""

    def __init__(self, store: StateStore | None = None):
        self._store = store

    def select(self, question: str, user_id: str = 'default') -> dict:
        from library._core.runtime.frame import select_frame
        return select_frame(question, user_id=user_id, store=self._store)


class DefaultSynthesizer:
    """Wraps ``synthesize.synthesize()``."""

    def __init__(self, store: StateStore | None = None):
        self._store = store

    def synthesize(self, question: str, user_id: str = 'default') -> dict:
        from library._core.runtime.synthesize import synthesize
        return synthesize(question, user_id=user_id, store=self._store)


class DefaultRenderer:
    """Wraps ``respond.render()``."""

    def render(self, data: dict, continuity: dict,
               mode: str = 'deep', voice: str = 'default') -> str:
        from library._core.runtime.respond import render
        return render(data, continuity, mode=mode, voice_mode=voice)


def create_default_runtime(user_id: str = 'default',
                           store: StateStore | None = None):
    """Assemble an ``AgentRuntime`` wired with production adapters."""
    from library.config import get_default_store
    from library._core.runtime.agent import AgentRuntime
    from library._adapters.sqlite_retriever import SqliteRetriever

    store = store or get_default_store()
    return AgentRuntime(
        retriever=SqliteRetriever(store=store),
        selector=DefaultFrameSelector(store=store),
        synthesizer=DefaultSynthesizer(store=store),
        renderer=DefaultRenderer(),
        store=store,
    )
