"""Domain and scope policy gateway for the Jordan agent.

This module runs before retrieval and frame selection. It centralizes
Jordan-specific domain boundaries so callers do not need to infer policy from
missing prompts or weak retrieval outcomes.
"""
from __future__ import annotations

from library._core.runtime.guardrails import (
    detect_out_of_domain,
    maybe_reset_out_of_domain_streak,
)
from library._core.runtime.routes import ALL_KB_KEYWORDS, infer_route
from library._core.state_store import StateStore

_WEATHER_KEYWORDS = [
    'погод', 'температур', 'дожд', 'снег', 'ветер', 'прогноз',
    'weather', 'forecast',
]

_NEWS_KEYWORDS = [
    'новост', 'что произошло сегодня', 'что случилось сегодня',
    'последние новости', 'latest news', 'breaking news',
]

_SHOPPING_KEYWORDS = [
    'бренд', 'марк', 'трус', 'бель', 'телефон', 'ноутбук', 'наушник',
    'кроссов', 'ботин', 'шампун', 'матрас', 'пылесос', 'автомоб', 'машин',
    'духи', 'косметик', 'одежд', 'куртк', 'плать', 'товар', 'product',
]

_SHOPPING_DECISION_KEYWORDS = [
    'лучше', 'хуже', 'сравни', 'сравнение', 'что выбрать', 'какой выбрать',
    'какой лучше', 'что лучше', 'vs', 'versus', 'или',
]

_SHOPPING_RECOMMENDATION_KEYWORDS = [
    'посоветуй', 'порекомендуй', 'рекомендуй', 'стоит ли покупать',
    'какой купить', 'что купить',
]

_TECH_KEYWORDS = [
    'напиши код', 'код', 'python', 'javascript', 'typescript', 'sql',
    'regex', 'api', 'stack trace', 'traceback', 'ошибка', 'баг',
    'программир', 'debug', 'refactor this code',
]

_MEDICAL_KEYWORDS = [
    'диагноз', 'симптом', 'симптомы', 'лекарств', 'таблет', 'болит',
    'анализы', 'анализ', 'врач', 'терапевт', 'депрессия лечится',
]

_LEGAL_FINANCIAL_KEYWORDS = [
    'налог', 'ипотек', 'кредит', 'договор', 'суд', 'закон', 'законно',
    'инвестиц', 'акци', 'облигац', 'биткоин', 'btc', 'crypto', 'крипт',
    'ставка цб', 'финансов',
]

_DOMAIN_EXTRA_KEYWORDS = [
    'смысл', 'призвание', 'карьер', 'дисциплин', 'хаос', 'обид', 'гореч',
    'стыд', 'позор', 'самообман', 'правд', 'вина', 'ответствен',
    'отношен', 'брак', 'жена', 'муж', 'ребен', 'родител', 'зависим',
    'страдан', 'трагед', 'избег', 'прокраст', 'страх', 'цен',
]


def _contains_any(q: str, keywords: list[str]) -> bool:
    return any(kw in q for kw in keywords)


def _looks_like_shopping_choice(q: str) -> bool:
    has_product = _contains_any(q, _SHOPPING_KEYWORDS)
    has_decision = (
        _contains_any(q, _SHOPPING_DECISION_KEYWORDS)
        or _contains_any(q, _SHOPPING_RECOMMENDATION_KEYWORDS)
    )
    return has_product and has_decision


def is_jordan_domain_candidate(question: str) -> bool:
    """Return True when the question looks plausibly in-domain for Jordan.

    This is intentionally permissive. We only want a coarse domain hint here,
    not the final policy decision.
    """
    q = (question or '').strip().lower()
    if not q:
        return False
    if infer_route(q) != 'general':
        return True
    if _contains_any(q, _DOMAIN_EXTRA_KEYWORDS):
        return True
    return any(kw in q for kw in ALL_KB_KEYWORDS)


def classify_scope_mismatch(question: str) -> dict | None:
    """Classify clearly off-scope queries for the Jordan assistant."""
    q = (question or '').strip().lower()
    if not q:
        return None

    if _contains_any(q, _WEATHER_KEYWORDS):
        return {
            'category': 'out_of_domain',
            'kind': 'weather-request',
            'intent': 'operational-fact-request',
            'bridgeable': False,
            'topic': 'weather',
        }

    if _contains_any(q, _NEWS_KEYWORDS):
        return {
            'category': 'out_of_domain',
            'kind': 'current-events',
            'intent': 'current-events-request',
            'bridgeable': False,
            'topic': 'news',
        }

    if _contains_any(q, _MEDICAL_KEYWORDS):
        return {
            'category': 'out_of_domain',
            'kind': 'medical-advice',
            'intent': 'high-stakes-advice',
            'bridgeable': False,
            'topic': 'medical',
        }

    if _contains_any(q, _LEGAL_FINANCIAL_KEYWORDS):
        return {
            'category': 'out_of_domain',
            'kind': 'legal-financial-advice',
            'intent': 'high-stakes-advice',
            'bridgeable': False,
            'topic': 'legal-financial',
        }

    if _contains_any(q, _TECH_KEYWORDS):
        return {
            'category': 'out_of_domain',
            'kind': 'technical-help',
            'intent': 'general-utility-request',
            'bridgeable': False,
            'topic': 'technical',
        }

    if _looks_like_shopping_choice(q):
        return {
            'category': 'out_of_domain',
            'kind': 'shopping-comparison',
            'intent': 'consumer-choice-request',
            'bridgeable': True,
            'topic': 'choice-values-self-image',
        }

    return None


def _render_scope_message(classification: dict) -> str:
    kind = classification.get('kind')

    if kind == 'shopping-comparison':
        return (
            'Я не выбираю бренды, товары или покупки в режиме consumer advice. '
            'Если вопрос на самом деле не о белье, а о том, по каким критериям '
            'ты выбираешь между статусом, комфортом, ценой, вкусом и образом '
            'себя, сформулируй это так, и я разберу именно структуру выбора.'
        )

    if kind == 'weather-request':
        return (
            'Я не работаю как прогноз погоды или справочник по текущей погоде. '
            'Если вопрос на самом деле о тревоге, подготовке, дисциплине или '
            'принятии решения под неопределенностью, сформулируй это прямо.'
        )

    if kind == 'current-events':
        return (
            'Я не комментирую оперативные новости и текущую повестку как '
            'универсальный новостной ассистент. Если тебе нужен разбор не '
            'новости, а твоей реакции на нее — страха, цинизма, растерянности '
            'или морального конфликта — тогда сформулируй это так.'
        )

    if kind == 'technical-help':
        return (
            'Я не работаю как универсальный coding assistant или техподдержка. '
            'Этот агент предназначен для психологических, моральных, '
            'экзистенциальных и дисциплинарных вопросов.'
        )

    if kind == 'medical-advice':
        return (
            'Я не даю медицинские советы, диагнозы или рекомендации по лечению. '
            'Если вопрос в том, как ты психологически переживаешь болезнь, страх '
            'или уязвимость, это можно разбирать отдельно — но не подменяя врача.'
        )

    if kind == 'legal-financial-advice':
        return (
            'Я не даю юридические или финансовые рекомендации как профильный '
            'советник. Если тебе нужно разобрать страх, избегание, жадность, '
            'стыд, конфликт ценностей или ответственность в решении, это уже '
            'другая постановка, и с ней можно работать.'
        )

    return (
        'Этот вопрос выходит за рабочую область данного агента. '
        'Сформулируй его через поведение, конфликт, ответственность, страх, '
        'стыд, resentment, дисциплину или смысл, если тебе нужен разбор именно '
        'в Jordan-рамке.'
    )


def detect_policy_block(question: str, user_id: str = 'default',
                        store: StateStore | None = None) -> dict | None:
    """Return a policy block result before retrieval, or None when allowed."""
    legacy = detect_out_of_domain(question, user_id=user_id, store=store)
    if legacy:
        return {
            **legacy,
            'policy_source': 'legacy-guardrail',
            'domain_status': legacy.get('category') or 'out_of_domain',
        }

    # Clear adaptive legacy streaks once the user leaves those legacy categories,
    # even if the new question is still out-of-scope for Jordan.
    maybe_reset_out_of_domain_streak(question, user_id=user_id, store=store)

    classification = classify_scope_mismatch(question)
    if not classification:
        return None

    return {
        **classification,
        'level': 'hard',
        'mode': 'policy-block',
        'message': _render_scope_message(classification),
        'policy_source': 'scope-gateway',
        'domain_status': classification.get('category') or 'out_of_domain',
    }
