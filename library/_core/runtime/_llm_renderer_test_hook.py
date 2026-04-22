"""Test-only hook used by llm renderer regressions."""
from __future__ import annotations


def render_text(*, request, prompt, attempt, violations):
    return 'Тогда назовём основу прямо: крепкие отношения держатся на правде, уважении и добровольно принятой ответственности. Что из этого ты хочешь разобрать глубже?'
