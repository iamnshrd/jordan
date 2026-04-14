"""Contract interfaces for the Jordan agent runtime.

Using ``typing.Protocol`` for structural subtyping -- implementations do not
need to inherit from these classes, they just need to expose matching methods.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


# -- data objects ----------------------------------------------------------

@dataclass(frozen=True)
class Query:
    text: str
    user_id: str = 'default'
    session_id: str = ''


@dataclass(frozen=True)
class RetrievalHit:
    chunk_id: int
    snippet: str
    score: float
    source: str | None = None
    meta: dict = field(default_factory=dict)


# -- protocols -------------------------------------------------------------

@runtime_checkable
class Retriever(Protocol):
    """Searches the knowledge base and returns scored hits."""

    def search(self, q: Query, k: int = 8) -> list[RetrievalHit]: ...

    def build_bundle(self, question: str, user_id: str = 'default') -> dict: ...


@runtime_checkable
class FrameSelector(Protocol):
    """Selects a psychological frame (theme / principle / pattern)."""

    def select(self, question: str, user_id: str = 'default') -> dict: ...


@runtime_checkable
class Synthesizer(Protocol):
    """Combines frame, KB query, and progress into a response bundle."""

    def synthesize(self, question: str, user_id: str = 'default') -> dict: ...


@runtime_checkable
class Renderer(Protocol):
    """Renders synthesized data + continuity into user-facing text."""

    def render(self, data: dict, continuity: dict,
               mode: str = 'deep', voice: str = 'default') -> str: ...
