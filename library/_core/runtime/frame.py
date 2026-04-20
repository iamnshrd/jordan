"""Frame selection -- choose theme, principle, pattern for a question.

Restructured from: select_frame.py
"""
from __future__ import annotations

from library._core.runtime.retrieve import build_response_bundle
from library._core.state_store import StateStore
from library.utils import timed
from library.config import canonical_user_id


def infer_route_name(question):
    """Delegate to canonical route registry."""
    from library._core.runtime.routes import infer_route
    return infer_route(question)


def _is_success_structure_question(question: str) -> bool:
    q = (question or '').lower()
    markers = [
        'успеш', 'успех', 'преусп', 'какие качества', 'какие привычки',
        'что отличает', 'что общего', 'талант', 'successful', 'success',
    ]
    return any(marker in q for marker in markers)


def choose_theme(bundle, question):
    q = question.lower()
    rows = bundle.get('top_themes', [])
    route_name = infer_route_name(question)

    if route_name == 'career-vocation':
        for preferred in ['meaning', 'responsibility', 'order-and-chaos']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'career-vocation route tie-break'

    if route_name == 'fear-value':
        for preferred in ['meaning', 'suffering', 'responsibility']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'fear-value route tie-break'

    if route_name == 'tragedy-suffering':
        for preferred in ['suffering', 'meaning', 'truth']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'tragedy-suffering route tie-break'

    if route_name == 'parenting-overprotection':
        for preferred in ['responsibility', 'order-and-chaos', 'truth']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'parenting route tie-break'

    if route_name == 'relationship-maintenance':
        for preferred in ['responsibility', 'truth', 'resentment']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'relationship route tie-break'

    if _is_success_structure_question(question):
        for preferred in ['responsibility', 'order-and-chaos', 'meaning']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'success-structure tie-break'

    if any(x in q for x in ['смысл', 'направление', 'цель', 'дисциплин', 'туман', 'размыт', 'плыть по течению', 'нет жизни', 'нет структуры']):
        for preferred in ['meaning', 'responsibility', 'order-and-chaos']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'meaning-loss tie-break'

    if any(x in q for x in ['обид', 'гореч', 'несправед', 'злость']):
        for preferred in ['resentment', 'responsibility']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'resentment tie-break'

    if any(x in q for x in ['отношен', 'партнер', 'конфликт', 'жена', 'муж',
                             'ребен', 'дет', 'воспит', 'родител', 'тирана']):
        if any(x in q for x in ['обид', 'скрытая обида', 'невысказан', 'цепляем друг друга', 'цепляем']):
            for preferred in ['responsibility', 'truth', 'resentment']:
                for row in rows:
                    if row['name'] == preferred:
                        return row, 'relationship resentment tie-break'
        if any(x in q for x in ['ребен', 'дет', 'воспит', 'родител',
                                 'тирана']):
            for preferred in ['responsibility', 'order-and-chaos', 'truth']:
                for row in rows:
                    if row['name'] == preferred:
                        return row, 'parenting tie-break'
        for preferred in ['responsibility', 'truth', 'resentment']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'relationship tie-break'

    if any(x in q for x in ['стыд', 'позор', 'отвращение к себе', 'никчем', 'ненавижу себя', 'ненависть к себе', 'self-contempt']):
        for preferred in ['suffering', 'responsibility', 'truth']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'shame tie-break'

    return (rows[0], 'top-score fallback') if rows else (None, 'no theme')


def choose_principle(bundle, question):
    q = question.lower()
    rows = bundle.get('top_principles', [])
    route_name = infer_route_name(question)

    if route_name == 'career-vocation':
        for preferred in ['take-responsibility-before-blame',
                          'clean-up-what-is-in-front-of-you']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'career-vocation route tie-break'

    if route_name == 'fear-value':
        for preferred in ['take-responsibility-before-blame',
                          'clean-up-what-is-in-front-of-you']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'fear-value route tie-break'

    if route_name == 'tragedy-suffering':
        for preferred in ['tell-the-truth-or-at-least-dont-lie',
                          'take-responsibility-before-blame']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'tragedy-suffering route tie-break'

    if route_name == 'parenting-overprotection':
        for preferred in ['clean-up-what-is-in-front-of-you',
                          'tell-the-truth-or-at-least-dont-lie',
                          'take-responsibility-before-blame']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'parenting route tie-break'

    if route_name == 'relationship-maintenance':
        for preferred in ['tell-the-truth-or-at-least-dont-lie',
                          'take-responsibility-before-blame',
                          'clean-up-what-is-in-front-of-you']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'relationship route tie-break'

    if _is_success_structure_question(question):
        for preferred in ['clean-up-what-is-in-front-of-you',
                          'take-responsibility-before-blame']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'success-structure tie-break'

    if any(x in q for x in ['дисциплин', 'хаос', 'беспоряд',
                             'не могу начать', 'жестк', 'расписан', 'график']):
        for preferred in ['clean-up-what-is-in-front-of-you',
                          'take-responsibility-before-blame']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'discipline/order tie-break'

    if any(x in q for x in ['смысл', 'направление', 'цель', 'туман', 'размыт', 'плыть по течению', 'нет жизни', 'нет структуры']):
        for preferred in ['take-responsibility-before-blame',
                          'clean-up-what-is-in-front-of-you']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'meaning-direction tie-break'

    if any(x in q for x in ['отношен', 'партнер', 'конфликт', 'жена', 'муж',
                             'ребен', 'дет', 'воспит', 'родител', 'тирана']):
        if any(x in q for x in ['ребен', 'дет', 'воспит', 'родител',
                                 'тирана']):
            for preferred in ['clean-up-what-is-in-front-of-you',
                              'tell-the-truth-or-at-least-dont-lie',
                              'take-responsibility-before-blame']:
                for row in rows:
                    if row['name'] == preferred:
                        return row, 'parenting tie-break'
        for preferred in ['tell-the-truth-or-at-least-dont-lie',
                          'take-responsibility-before-blame']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'relationship tie-break'

    if any(x in q for x in ['стыд', 'позор', 'отвращение к себе', 'никчем', 'ненавижу себя', 'ненависть к себе', 'self-contempt']):
        for preferred in ['take-responsibility-before-blame',
                          'tell-the-truth-or-at-least-dont-lie']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'shame tie-break'

    if any(x in q for x in ['вру', 'самообман', 'лож', 'честн']):
        for preferred in ['tell-the-truth-or-at-least-dont-lie']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'truth tie-break'

    return (rows[0], 'top-score fallback') if rows else (None, 'no principle')


def choose_pattern(bundle, question):
    q = question.lower()
    rows = bundle.get('top_patterns', [])
    route_name = infer_route_name(question)

    if route_name == 'career-vocation':
        for preferred in ['aimlessness', 'avoidance-loop']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'career-vocation route tie-break'

    if route_name == 'fear-value':
        for preferred in ['avoidance-loop', 'aimlessness']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'fear-value route tie-break'

    if route_name == 'tragedy-suffering':
        for preferred in ['resentment-loop', 'avoidance-loop', 'aimlessness']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'tragedy-suffering route tie-break'

    if route_name == 'shame-self-contempt':
        for preferred in ['avoidance-loop', 'aimlessness', 'resentment-loop']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'shame-self-contempt route tie-break'

    if route_name == 'parenting-overprotection':
        for preferred in ['avoidance-loop', 'resentment-loop', 'aimlessness']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'parenting route tie-break'

    if route_name == 'relationship-maintenance':
        for preferred in ['resentment-loop', 'avoidance-loop', 'aimlessness']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'relationship route tie-break'

    if _is_success_structure_question(question):
        for preferred in ['aimlessness', 'avoidance-loop']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'success-structure tie-break'

    if any(x in q for x in ['смысл', 'направление', 'цель', 'туман', 'размыт', 'плыть по течению', 'нет жизни', 'нет структуры']):
        for preferred in ['aimlessness', 'avoidance-loop']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'meaning-direction tie-break'

    if any(x in q for x in ['избег', 'прокраст', 'не могу начать',
                             'отклады']):
        for preferred in ['avoidance-loop', 'aimlessness']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'avoidance tie-break'

    if any(x in q for x in ['отношен', 'партнер', 'конфликт', 'жена', 'муж']) and any(x in q for x in ['обид', 'гореч', 'невысказан', 'цепляем']):
        for preferred in ['resentment-loop', 'avoidance-loop']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'relationship resentment tie-break'

    if any(x in q for x in ['обид', 'гореч', 'злость']):
        for preferred in ['resentment-loop']:
            for row in rows:
                if row['name'] == preferred:
                    return row, 'resentment tie-break'

    return (rows[0], 'top-score fallback') if rows else (None, 'no pattern')


@timed('frame')
def select_frame(question, user_id: str = 'default',
                 store: StateStore | None = None):
    user_id = canonical_user_id(user_id)
    bundle = build_response_bundle(question, user_id=user_id, store=store)
    theme, theme_reason = choose_theme(bundle, question)
    principle, principle_reason = choose_principle(bundle, question)
    pattern, pattern_reason = choose_pattern(bundle, question)

    has_empty = any(r.startswith('no ') for r in
                     (theme_reason, principle_reason, pattern_reason))
    all_specific = all(r != 'top-score fallback' for r in
                       (theme_reason, principle_reason, pattern_reason))
    if has_empty:
        confidence = 'low'
    elif all_specific:
        confidence = 'high'
    else:
        confidence = 'medium'

    preferred_sources = bundle.get('preferred_sources')
    source_blend = None
    if preferred_sources and len(preferred_sources) >= 2:
        source_blend = {
            'primary': preferred_sources[0],
            'secondary': preferred_sources[1],
        }

    return {
        'question': question,
        'route_name': infer_route_name(question),
        'selected_theme': theme,
        'selected_theme_reason': theme_reason,
        'selected_principle': principle,
        'selected_principle_reason': principle_reason,
        'selected_pattern': pattern,
        'selected_pattern_reason': pattern_reason,
        'confidence': confidence,
        'preferred_sources': preferred_sources,
        'source_blend': source_blend,
        'bundle': bundle,
    }
