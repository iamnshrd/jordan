"""Retrieval validation -- check that retrieved chunks are relevant.

Provides a Self-RAG-inspired validation step.  When an LLM is available
(via OpenClaw), each retrieved chunk is scored for relevance.  Low-relevance
results trigger a fallback to ``ask-clarifying-question`` instead of
forcing an irrelevant frame.

Without an LLM, a lightweight heuristic scorer is used as a baseline.
Cross-language overlap is supported via synonym expansion from utils.SYNONYM_MAP.
"""
from __future__ import annotations

import re
from typing import Protocol

from library.utils import SYNONYM_MAP, get_threshold


class RelevanceJudge(Protocol):
    """Interface for LLM-based relevance scoring."""

    def score_relevance(self, question: str, chunk_text: str) -> float:
        """Return relevance score 0.0 - 1.0."""
        ...


_synonym_index: dict[str, set[str]] | None = None


def _build_synonym_index() -> dict[str, set[str]]:
    """Build a word→synonyms lookup from SYNONYM_MAP (once)."""
    global _synonym_index
    if _synonym_index is not None:
        return _synonym_index
    idx: dict[str, set[str]] = {}
    for key, synonyms in SYNONYM_MAP.items():
        group = {key} | set(synonyms)
        for word in group:
            idx.setdefault(word, set()).update(group)
    _synonym_index = idx
    return _synonym_index


def _expand_with_synonyms(words: set[str]) -> set[str]:
    """Expand a set of words with cross-language synonyms."""
    idx = _build_synonym_index()
    expanded = set(words)
    for w in words:
        if w in idx:
            expanded.update(idx[w])
        else:
            for key in idx:
                if w.startswith(key) or key.startswith(w):
                    expanded.update(idx[key])
    return expanded


def _word_overlap(question: str, text: str) -> float:
    """Heuristic relevance: word overlap with cross-language synonym expansion."""
    q_words = set(
        w for w in re.sub(r'[^\w\s]', ' ', question.lower()).split()
        if len(w) >= 3
    )
    t_words = set(
        w for w in re.sub(r'[^\w\s]', ' ', text.lower()).split()
        if len(w) >= 3
    )
    if not q_words:
        return 0.0
    q_expanded = _expand_with_synonyms(q_words)
    t_expanded = _expand_with_synonyms(t_words)
    overlap = q_expanded & t_expanded
    return len(overlap) / len(q_expanded) if q_expanded else 0.0


def heuristic_relevance(question: str, chunk_text: str) -> float:
    """Score relevance 0.0 - 1.0 using cross-language word overlap heuristic."""
    mult = get_threshold('heuristic_relevance_multiplier', 2.0)
    return min(1.0, _word_overlap(question, chunk_text) * mult)


def validate_chunks(question: str, chunks: list[dict],
                    judge: RelevanceJudge | None = None,
                    threshold: float | None = None) -> dict:
    """Validate retrieved chunks for relevance.

    Parameters
    ----------
    question : str
        The user's question.
    chunks : list[dict]
        Retrieved chunk dicts (must have ``snippet`` or ``content`` key).
    judge : RelevanceJudge or None
        LLM-based judge.  Falls back to heuristic if None.
    threshold : float
        Minimum average relevance to accept the retrieval.

    Returns
    -------
    dict with:
        ``valid``: bool - whether retrieval passes validation
        ``avg_relevance``: float - average relevance across chunks
        ``scored_chunks``: list[dict] - chunks with ``relevance`` field added
        ``action``: str - ``'accept'`` or ``'ask-clarifying-question'``
    """
    if threshold is None:
        threshold = get_threshold('retrieval_validation_threshold', 0.3)
    if not chunks:
        return {
            'valid': False,
            'avg_relevance': 0.0,
            'scored_chunks': [],
            'action': 'ask-clarifying-question',
        }

    import logging
    log = logging.getLogger('jordan')
    scored: list[dict] = []
    total = 0.0
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        text = chunk.get('snippet') or chunk.get('content') or ''
        if judge is not None:
            try:
                relevance = judge.score_relevance(question, text)
                relevance = max(0.0, min(1.0, float(relevance)))
            except Exception as exc:
                log.warning('LLM judge failed, falling back to heuristic: %s', exc)
                relevance = heuristic_relevance(question, text)
        else:
            relevance = heuristic_relevance(question, text)
        scored.append({**chunk, 'relevance': round(relevance, 3)})
        total += relevance

    avg = total / len(scored) if scored else 0.0

    scored.sort(key=lambda x: -x['relevance'])

    return {
        'valid': avg >= threshold,
        'avg_relevance': round(avg, 3),
        'scored_chunks': scored,
        'action': 'accept' if avg >= threshold else 'ask-clarifying-question',
    }


_default_judge: RelevanceJudge | None = None


def set_relevance_judge(judge: RelevanceJudge):
    """Register an LLM-based relevance judge for use in validate_chunks."""
    global _default_judge
    _default_judge = judge


def get_relevance_judge() -> RelevanceJudge | None:
    """Return the registered LLM judge, or None."""
    return _default_judge


def build_relevance_prompt(question: str, chunk_text: str) -> dict:
    """Build a prompt for LLM-based relevance scoring.

    Returns a dict with ``system`` and ``user`` for OpenClaw to call.
    The LLM should respond with a single float between 0.0 and 1.0.
    """
    return {
        'system': (
            'Ты — судья релевантности. Оцени, насколько данный фрагмент текста '
            'релевантен вопросу пользователя. Ответь ТОЛЬКО одним числом от 0.0 до 1.0.\n'
            '0.0 = совершенно не релевантен\n'
            '0.5 = частично релевантен\n'
            '1.0 = прямо отвечает на вопрос\n'
            'Отвечай ТОЛЬКО числом, без пояснений.'
        ),
        'user': f'Вопрос: {question}\n\nФрагмент: {chunk_text[:1000]}',
    }
