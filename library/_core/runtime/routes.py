"""Canonical route registry — single source of truth for route names and keywords.

Every module that needs to classify questions by route should import from here
instead of maintaining its own keyword lists.
"""
from __future__ import annotations

ROUTES: dict[str, dict] = {
    'shame-self-contempt': {
        'keywords': ['стыд', 'позор', 'отвращение к себе', 'никчем',
                     'омерзен', 'ненавижу себя', 'self-contempt'],
        'voice_bias': 'reflective',
    },
    'relationship-maintenance': {
        'keywords': ['отношен', 'партнер', 'конфликт', 'жена', 'муж',
                     'брак', 'ссор', 'невысказан', 'цепляем друг друга',
                     'цепляем', 'друг друга'],
        'voice_bias': None,
    },
    'career-vocation': {
        'keywords': ['карьер', 'призвание', 'путь', 'работ', 'туман',
                     'размыт', 'расплыва', 'расплывает', 'не понимаю, куда',
                     'куда мне двигаться', 'двигаться по жизни', 'нет направления',
                     'плыть по течению', 'нет жизни', 'нет структуры',
                     'бремя', 'выбранного бремени', 'направлен', 'ориентац',
                     'профес', 'vocation'],
        'voice_bias': None,
    },
    'addiction-chaos': {
        'keywords': ['зависим', 'алкогол', 'наркот', 'спиваюсь',
                     'addiction', 'хаос'],
        'voice_bias': 'hard',
    },
    'parenting-overprotection': {
        'keywords': ['ребен', 'дет', 'воспит', 'родител', 'тирана',
                     'parenting'],
        'voice_bias': None,
    },
    'avoidance-paralysis': {
        'keywords': ['отклады', 'прокраст', 'не могу начать', 'жестк',
                     'расписан', 'график', 'паралич', 'избегаю', 'avoid'],
        'voice_bias': 'hard',
    },
    'resentment': {
        'keywords': ['обид', 'гореч', 'злость', 'несправед', 'resentment'],
        'voice_bias': None,
    },
    'self-deception': {
        'keywords': ['вру', 'самообман', 'лож', 'честн', 'self-deception',
                     'lie to myself', 'tell the truth'],
        'voice_bias': 'hard',
    },
}

ALL_KB_KEYWORDS: list[str] = sorted(
    {kw for route in ROUTES.values() for kw in route['keywords']}
)


def infer_route(question: str) -> str:
    """Return the best-matching route name for *question*, or 'general'.

    Scores each route by number of keyword hits; highest wins.
    """
    q = question.lower()
    best_route = 'general'
    best_score = 0
    for route_name, spec in ROUTES.items():
        score = sum(1 for kw in spec['keywords'] if kw in q)
        if score > best_score:
            best_score = score
            best_route = route_name
    return best_route


def route_voice_bias(route_name: str) -> str | None:
    """Return the voice bias for a route, or None."""
    spec = ROUTES.get(route_name)
    return spec['voice_bias'] if spec else None
