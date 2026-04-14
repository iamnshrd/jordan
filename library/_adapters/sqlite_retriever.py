"""SQLite-backed Retriever adapter wrapping the existing retrieve module."""
from __future__ import annotations

from library._core.protocols import Query, RetrievalHit
from library._core.state_store import StateStore
from library._core.runtime.retrieve import (
    build_response_bundle,
    search_chunks as _search_chunks,
)
from library.db import connect
from library.utils import fts_query


class SqliteRetriever:
    """Retriever implementation backed by SQLite FTS + evidence tables."""

    def __init__(self, store: StateStore | None = None):
        self._store = store

    def search(self, q: Query, k: int = 8) -> list[RetrievalHit]:
        with connect() as conn:
            cur = conn.cursor()
            rows = _search_chunks(cur, q.text, limit=k)
        return [
            RetrievalHit(
                chunk_id=row['id'],
                snippet=row.get('snippet', ''),
                score=float(row.get('_score', 0)),
                source=None,
                meta=row,
            )
            for row in rows
        ]

    def build_bundle(self, question: str,
                     user_id: str = 'default') -> dict:
        return build_response_bundle(
            question, user_id=user_id, store=self._store,
        )
