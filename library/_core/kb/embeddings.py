"""Embeddings infrastructure for hybrid retrieval.

Provides storage, retrieval, and cosine-similarity re-ranking of chunk
embeddings.  Embedding generation is handled externally (by OpenClaw or
any provider that implements ``EmbeddingProvider``).

Usage
-----
1. **Generate embeddings** by passing chunks to an external provider
   (e.g. OpenAI ``text-embedding-3-small``, ``e5-small``, etc.)
2. **Store** them with :func:`store_embeddings`.
3. At query time, use :func:`hybrid_search` which combines FTS BM25
   candidates with cosine-similarity re-ranking.
"""
from __future__ import annotations

import struct
from typing import Protocol, Sequence

from library.db import connect, row_to_dict
from library.utils import fts_query


class EmbeddingProvider(Protocol):
    """Interface for external embedding generation."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for each text."""
        ...

    @property
    def model_name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...


_registered_provider: EmbeddingProvider | None = None


def set_embedding_provider(provider: EmbeddingProvider) -> None:
    global _registered_provider
    _registered_provider = provider


def get_embedding_provider() -> EmbeddingProvider | None:
    return _registered_provider


def _pack_floats(vec: Sequence[float]) -> bytes:
    return struct.pack(f'{len(vec)}f', *vec)


def _unpack_floats(blob: bytes, dim: int) -> list[float] | None:
    expected = dim * 4
    if len(blob) != expected:
        return None
    return list(struct.unpack(f'{dim}f', blob))


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def store_embeddings(chunk_ids: list[int], vectors: list[list[float]],
                     model_name: str, dimensions: int, conn=None):
    """Persist embeddings for the given chunk IDs."""
    if len(chunk_ids) != len(vectors):
        raise ValueError(
            f'chunk_ids ({len(chunk_ids)}) and vectors ({len(vectors)}) length mismatch'
        )

    def _write(c):
        cur = c.cursor()
        for cid, vec in zip(chunk_ids, vectors):
            if len(vec) != dimensions:
                raise ValueError(
                    f'Vector for chunk {cid} has {len(vec)} dims, expected {dimensions}'
                )
            blob = _pack_floats(vec)
            cur.execute(
                'INSERT OR REPLACE INTO chunk_embeddings '
                '(chunk_id, model_name, embedding, dimensions) VALUES (?, ?, ?, ?)',
                (cid, model_name, blob, dimensions),
            )

    if conn is not None:
        _write(conn)
    else:
        with connect() as c:
            _write(c)


def embed_all_chunks(provider: EmbeddingProvider, batch_size: int = 64):
    """Generate and store embeddings for all chunks missing them."""
    with connect() as conn:
        rows = conn.cursor().execute(
            'SELECT dc.id, dc.content FROM document_chunks dc '
            'JOIN documents d ON d.id = dc.document_id '
            'LEFT JOIN chunk_embeddings ce ON ce.chunk_id = dc.id AND ce.model_name = ? '
            'WHERE dc.revision_id = d.active_revision_id AND ce.chunk_id IS NULL',
            (provider.model_name,),
        ).fetchall()

    if not rows:
        return {'embedded': 0, 'model': provider.model_name}

    total = 0
    with connect() as conn:
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            ids = [r[0] for r in batch]
            texts = [r[1] for r in batch]
            vectors = provider.embed(texts)
            if len(vectors) != len(texts):
                raise ValueError(
                    f'Provider returned {len(vectors)} vectors for '
                    f'{len(texts)} texts (batch starting at index {i})'
                )
            store_embeddings(ids, vectors, provider.model_name,
                             provider.dimensions, conn=conn)
            total += len(batch)

    return {'embedded': total, 'model': provider.model_name}


def hybrid_search(query_text: str, query_embedding: list[float] | None = None,
                  fts_limit: int = 20, final_limit: int = 5,
                  alpha: float = 0.4) -> list[dict]:
    """Hybrid retrieval: FTS BM25 candidates re-ranked by cosine similarity.

    Parameters
    ----------
    query_text : str
        Natural-language query for FTS.
    query_embedding : list[float] or None
        Pre-computed embedding of the query.  If None, falls back to pure FTS.
    fts_limit : int
        Number of FTS candidates to retrieve before re-ranking.
    final_limit : int
        Number of results to return.
    alpha : float
        Weight for FTS score in hybrid: ``alpha * fts + (1-alpha) * cosine``.

    Returns
    -------
    list[dict]
        Chunk dicts with ``id``, ``chunk_index``, ``snippet``, ``hybrid_score``.
    """
    fts_q = fts_query(query_text)
    with connect() as conn:
        cur = conn.cursor()

        if not fts_q:
            return []

        cur.execute(
            """
            SELECT dc.id, dc.chunk_index, dc.content,
                   snippet(document_chunks_fts, 0, '[', ']', ' … ', 16) AS snippet,
                   bm25(document_chunks_fts) AS bm25_rank
            FROM document_chunks_fts fts
            JOIN document_chunks dc ON dc.id = fts.rowid
            JOIN documents d ON d.id = dc.document_id
            WHERE dc.revision_id = d.active_revision_id
              AND document_chunks_fts MATCH ?
            ORDER BY bm25(document_chunks_fts)
            LIMIT ?
            """,
            (fts_q, fts_limit),
        )
        fts_rows = [row_to_dict(cur, r) for r in cur.fetchall()]

        if not fts_rows:
            return []

        if query_embedding is None:
            for r in fts_rows[:final_limit]:
                r['hybrid_score'] = -r.get('bm25_rank', 0)
            return fts_rows[:final_limit]

        chunk_ids = [r['id'] for r in fts_rows]
        placeholders = ','.join(['?'] * len(chunk_ids))
        cur.execute(
            f'SELECT chunk_id, embedding, dimensions FROM chunk_embeddings '
            f'WHERE chunk_id IN ({placeholders})',
            chunk_ids,
        )
        emb_map: dict[int, list[float]] = {}
        for row in cur.fetchall():
            vec = _unpack_floats(row[1], row[2])
            if vec is not None:
                emb_map[row[0]] = vec

    bm25_scores = [-r.get('bm25_rank', 0) for r in fts_rows]
    max_bm25 = max(bm25_scores) if bm25_scores else 1.0
    if max_bm25 == 0:
        max_bm25 = 1.0

    for i, r in enumerate(fts_rows):
        norm_fts = bm25_scores[i] / max_bm25
        emb = emb_map.get(r['id'])
        if emb:
            cos_sim = _cosine_similarity(query_embedding, emb)
            cos_norm = (cos_sim + 1.0) / 2.0
        else:
            cos_sim = None
            cos_norm = 0.3  # penalty: no embedding → below neutral
        r['hybrid_score'] = alpha * norm_fts + (1 - alpha) * cos_norm
        r['cosine_sim'] = cos_sim

    fts_rows.sort(key=lambda x: -x['hybrid_score'])
    return fts_rows[:final_limit]
