from __future__ import annotations

import re

from library._core.state_store import StateStore

ASTROLOGY_KEYWORDS = [
    'астролог', 'астрология', 'гороскоп', 'натальная карта', 'натал',
    'знак зодиака', 'зодиак', 'овен', 'телец', 'близнец', 'рак', 'лев',
    'дева', 'весы', 'скорпион', 'стрелец', 'козерог', 'водолей', 'рыбы',
    'совместимость по знакам', 'по знакам', 'по планетам', 'планет',
    'меркурий', 'венера', 'марс', 'юпитер', 'сатурн', 'ретроград',
]

ESOTERIC_KEYWORDS = [
    'таро', 'карты таро', 'расклад', 'руны', 'матрица судьбы', 'нумерология',
    'эзотер', 'чакр', 'карма', 'кармическ', 'энергетик', 'энергии',
]

FORTUNE_TELLING_KEYWORDS = [
    'что будет', 'предскажи', 'предсказ', 'скажи будущее', 'какое будущее',
    'что нас ждет', 'что меня ждет', 'судьба', 'суждено', 'предначертан',
]

ROLEPLAY_BAIT_KEYWORDS = [
    'ответь как', 'сыграй роль', 'прикинься', 'roleplay', 'будь моим',
    'говори как', 'в образе',
]

PSEUDO_CERTAINTY_KEYWORDS = [
    'точно скажи', 'дай точный ответ', 'скажи наверняка', 'без сомнений',
    'однозначно скажи', 'просто скажи да или нет',
]

KEY_DOMAIN_GUARDRAILS = 'domain_guardrails'

_EXACT_TOKEN_GUARDRAIL_KEYWORDS = {
    'овен', 'телец', 'близнец', 'рак', 'лев', 'дева', 'весы',
    'скорпион', 'стрелец', 'козерог', 'водолей', 'рыбы',
    'меркурий', 'венера', 'марс', 'юпитер', 'сатурн',
}


def _contains_any(q: str, keywords: list[str]) -> bool:
    tokens = [
        token for token in re.sub(r'[^\w\s-]', ' ', q).split()
        if token
    ]
    token_set = set(tokens)
    for kw in keywords:
        needle = (kw or '').lower().strip()
        if not needle:
            continue
        if needle in _EXACT_TOKEN_GUARDRAIL_KEYWORDS:
            if needle in token_set:
                return True
            continue
        if ' ' in needle:
            if needle in q:
                return True
            continue
        if needle in q:
            return True
    return False


def _load_guardrail_state(user_id: str, store: StateStore | None) -> dict:
    if store is None:
        return {}
    return store.get_json(user_id, KEY_DOMAIN_GUARDRAILS, default={}) or {}


def _save_guardrail_state(user_id: str, state: dict, store: StateStore | None) -> None:
    if store is None:
        return
    store.put_json(user_id, KEY_DOMAIN_GUARDRAILS, state)


def classify_guardrail(question: str) -> dict | None:
    q = (question or '').lower()

    if _contains_any(q, ASTROLOGY_KEYWORDS):
        return {
            'category': 'out_of_domain',
            'kind': 'astrology',
            'intent': 'comforting-nonsense-request',
            'bridgeable': True,
            'topic': 'temperament-conflict-boundaries',
        }
    if _contains_any(q, ESOTERIC_KEYWORDS):
        return {
            'category': 'out_of_domain',
            'kind': 'esoteric',
            'intent': 'comforting-nonsense-request',
            'bridgeable': True,
            'topic': 'psychology-conflict-self-deception',
        }
    if _contains_any(q, FORTUNE_TELLING_KEYWORDS):
        return {
            'category': 'pseudo-certainty',
            'kind': 'fortune-telling',
            'intent': 'delegation-of-judgment',
            'bridgeable': True,
            'topic': 'choice-risk-responsibility',
        }
    if _contains_any(q, ROLEPLAY_BAIT_KEYWORDS):
        return {
            'category': 'persona-boundary',
            'kind': 'roleplay-bait',
            'intent': 'boundary-testing',
            'bridgeable': False,
            'topic': 'direct-conversation',
        }
    if _contains_any(q, PSEUDO_CERTAINTY_KEYWORDS):
        return {
            'category': 'pseudo-certainty',
            'kind': 'certainty-demand',
            'intent': 'delegation-of-judgment',
            'bridgeable': True,
            'topic': 'uncertainty-judgment-responsibility',
        }
    return None


def _adaptive_mode(streak: int, classification: dict) -> str:
    category = classification.get('category')
    if category == 'persona-boundary':
        return 'boundary-enforcement'
    if streak <= 1:
        return 'soft-redirect'
    if streak == 2:
        return 'firm-redirect'
    if classification.get('bridgeable'):
        return 'confront-and-bridge'
    return 'refuse-and-close'


def _render_bridge(topic: str) -> str:
    if topic == 'temperament-conflict-boundaries':
        return 'Опиши лучше, кто из вас давит, кто уходит, где копится обида и какие границы не названы прямо.'
    if topic == 'psychology-conflict-self-deception':
        return 'Опиши факты, повторяющийся конфликт, самообман, страх или избегание, если тебе нужен реальный разбор.'
    if topic == 'choice-risk-responsibility':
        return 'Полезный вопрос здесь не "что будет", а какие у тебя варианты, риски, слепые зоны и за что ты сам отвечаешь.'
    if topic == 'uncertainty-judgment-responsibility':
        return 'Формулируй вопрос через неопределенность, критерии решения, риск и ответственность, а не через требование магической точности.'
    return 'Формулируй вопрос через реальные факты, поведение, конфликт, выбор и ответственность.'


def _render_message(classification: dict, streak: int, mode: str) -> str:
    kind = classification.get('kind')
    bridge = _render_bridge(classification.get('topic') or '')

    if kind == 'astrology':
        if mode == 'soft-redirect':
            return (
                'Я не разбираю отношения, характер или решения через астрологию, '
                'знаки зодиака или "планеты". ' + bridge
            )
        if mode == 'firm-redirect':
            return (
                'Ты снова уводишь вопрос в астрологическую схему, которая не даёт '
                'реальной ясности. ' + bridge
            )
        return (
            'Нет. Я не буду подменять анализ астрологической сказкой. '
            'Говори о фактах, выборе, избегании, обиде, ответственности и '
            'характере. ' + bridge
        )

    if kind == 'esoteric':
        if mode == 'soft-redirect':
            return (
                'Я не работаю через эзотерику, таро, руны или подобные схемы. '
                + bridge
            )
        if mode == 'firm-redirect':
            return (
                'Ты снова пытаешься вынести вопрос в эзотерическую схему вместо '
                'разбора реального поведения и выбора. ' + bridge
            )
        return (
            'Нет. Я не буду подыгрывать эзотерической конструкции вместо анализа. '
            + bridge
        )

    if kind == 'fortune-telling':
        if mode == 'soft-redirect':
            return 'Я не предсказываю будущее. ' + bridge
        if mode == 'firm-redirect':
            return 'Ты пытаешься снять с себя бремя суждения и риска через запрос предсказания. ' + bridge
        return 'Нет. Я не буду выдавать тебе успокоительное пророчество вместо мышления. ' + bridge

    if kind == 'certainty-demand':
        if mode == 'soft-redirect':
            return 'Я не дам тебе фальшивую абсолютную уверенность там, где требуется суждение. ' + bridge
        if mode == 'firm-redirect':
            return 'Ты снова требуешь магической определенности вместо взрослого решения под неопределенностью. ' + bridge
        return 'Нет. Требование абсолютной точности здесь выглядит как попытка не нести ответственность за собственное суждение. ' + bridge

    if kind == 'roleplay-bait':
        return (
            'Нет. Я не буду превращать разговор в ролевую игру или театральную '
            'маску. Если тебе нужен разбор, говори прямо о проблеме.'
        )

    return 'Формулируй вопрос через реальные факты, выбор, поведение и ответственность.'


def detect_out_of_domain(question: str, user_id: str = 'default',
                         store: StateStore | None = None) -> dict | None:
    classification = classify_guardrail(question)
    if not classification:
        return None

    state = _load_guardrail_state(user_id, store)
    streak = int(state.get('guardrail_streak', 0) or 0) + 1
    mode = _adaptive_mode(streak, classification)
    updated = {
        'last_kind': classification.get('kind'),
        'last_category': classification.get('category'),
        'last_intent': classification.get('intent'),
        'guardrail_streak': streak,
        'last_question': question,
        'last_mode': mode,
    }
    _save_guardrail_state(user_id, updated, store)

    return {
        **classification,
        'streak': streak,
        'level': 'soft' if streak <= 1 else 'firm' if streak == 2 else 'hard',
        'mode': mode,
        'message': _render_message(classification, streak, mode),
    }


def maybe_reset_out_of_domain_streak(question: str, user_id: str = 'default',
                                     store: StateStore | None = None) -> None:
    if store is None:
        return
    if classify_guardrail(question):
        return
    state = _load_guardrail_state(user_id, store)
    if not state:
        return
    if int(state.get('guardrail_streak', 0) or 0) <= 0:
        return
    state['guardrail_streak'] = 0
    state['last_mode'] = 'reset'
    _save_guardrail_state(user_id, state, store)
