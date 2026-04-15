from __future__ import annotations

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

KEY_DOMAIN_GUARDRAILS = 'domain_guardrails'


def _load_guardrail_state(user_id: str, store: StateStore | None) -> dict:
    if store is None:
        return {}
    return store.get_json(user_id, KEY_DOMAIN_GUARDRAILS, default={}) or {}


def _save_guardrail_state(user_id: str, state: dict, store: StateStore | None) -> None:
    if store is None:
        return
    store.put_json(user_id, KEY_DOMAIN_GUARDRAILS, state)


def _message_for(kind: str, streak: int) -> str:
    if kind == 'astrology':
        if streak <= 1:
            return (
                'Я не разбираю отношения, характер или решения через астрологию, '
                'знаки зодиака или "планеты". Если хочешь, я могу вместо этого '
                'разобрать ситуацию через темперамент, границы, конфликт, '
                'ответственность и невысказанные ожидания.'
            )
        if streak == 2:
            return (
                'Ты снова уводишь вопрос в астрологическую схему, которая не даёт '
                'реальной ясности. Если тебе нужен разбор, формулируй его через '
                'поведение, конфликт, страх, границы и ответственность.'
            )
        return (
            'Нет. Я не буду подменять анализ астрологической сказкой. Если ты '
            'хочешь понять, что происходит, говори о фактах, выборе, избегании, '
            'обиде, ответственности и характере. Иначе ты просто уходишь от сути.'
        )

    if streak <= 1:
        return (
            'Я не работаю через эзотерику, таро, руны или подобные схемы. '
            'Если хочешь, я могу разобрать это как вопрос психологии, '
            'поведения, самообмана, конфликта и ответственности.'
        )
    if streak == 2:
        return (
            'Ты снова пытаешься вынести вопрос в эзотерическую схему вместо '
            'разбора реального поведения и выбора. Если тебе нужна польза, '
            'опиши факты, конфликт, страх, избегание или ответственность.'
        )
    return (
        'Нет. Я не буду подыгрывать эзотерической конструкции вместо анализа. '
        'Если ты хочешь ясности, говори о реальном поведении, самообмане, '
        'конфликте, дисциплине и ответственности.'
    )


def detect_out_of_domain(question: str, user_id: str = 'default',
                         store: StateStore | None = None) -> dict | None:
    q = (question or '').lower()
    kind = None
    if any(kw in q for kw in ASTROLOGY_KEYWORDS):
        kind = 'astrology'
    elif any(kw in q for kw in ESOTERIC_KEYWORDS):
        kind = 'esoteric'

    if not kind:
        return None

    state = _load_guardrail_state(user_id, store)
    streak = int(state.get('out_of_domain_streak', 0) or 0) + 1
    updated = {
        'last_kind': kind,
        'out_of_domain_streak': streak,
        'last_question': question,
    }
    _save_guardrail_state(user_id, updated, store)

    level = 'soft' if streak <= 1 else 'firm' if streak == 2 else 'hard'
    return {
        'kind': kind,
        'streak': streak,
        'level': level,
        'message': _message_for(kind, streak),
    }


def maybe_reset_out_of_domain_streak(question: str, user_id: str = 'default',
                                     store: StateStore | None = None) -> None:
    if store is None:
        return
    if detect_out_of_domain(question, user_id=user_id, store=None):
        return
    state = _load_guardrail_state(user_id, store)
    if not state:
        return
    if int(state.get('out_of_domain_streak', 0) or 0) <= 0:
        return
    state['out_of_domain_streak'] = 0
    _save_guardrail_state(user_id, state, store)
