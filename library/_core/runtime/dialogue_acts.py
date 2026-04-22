"""Interpret what a user turn does relative to the active dialogue."""
from __future__ import annotations

from library._core.runtime.dialogue_state import is_scope_menu_question

_RELATIONSHIP_AXIS_MARKERS = {
    'resentment': ['обида', 'обиж', 'горечь'],
    'coldness': ['холод', 'холодность', 'отстраненность', 'отстранённость'],
    'loss_of_desire': ['желание', 'нет желания', 'потеря желания', 'утрата желания'],
    'loss_of_respect': ['уважение', 'нет уважения', 'утрата уважения'],
    'unspoken_conflict': ['конфликт', 'не высказано', 'невысказан', 'всё в порядке'],
}

_SELF_DIAGNOSIS_AXIS_MARKERS = {
    'emotional_flatness': ['пустота', 'эмоциональная пустота', 'ничего не чувствую'],
    'loss_of_interest': ['утрата интереса', 'нет интереса', 'ничего не интересно', 'интерес'],
    'exhaustion': ['бессилие', 'усталость', 'нет сил', 'истощение'],
    'social_disconnection': ['отрыв от людей', 'от людей', 'ни с кем', 'изоляция'],
    'loss_of_aim': ['ничто не зовёт', 'нет смысла', 'нет цели', 'ничего не тянет'],
}

_PORTRAIT_AXIS_MARKERS = {
    'discipline': ['дисциплина', 'хаос', 'собранность'],
    'closeness': ['близость', 'отношения', 'связь с людьми'],
    'resentment': ['обида', 'злость', 'горечь'],
    'avoidance': ['избегание', 'откладываю', 'прячусь'],
    'self_deception': ['самообман', 'вру себе', 'лгу себе'],
}

_SHAME_AXIS_MARKERS = {
    'humiliation': ['унижение', 'унижен', 'унижена', 'унизили'],
    'exposure': ['разоблачение', 'выставили', 'стыдно перед людьми', 'на людях', 'увидят', 'увидели'],
    'failure': ['провал', 'неудача', 'несостоятельность', 'облажался', 'облажалась'],
    'self_condemnation': ['ненависть к себе', 'самоненависть', 'отвращение к себе', 'я мерзок', 'я мерзка'],
    'resentment': ['обида', 'горечь', 'злюсь на себя'],
}

_RELATIONSHIP_DETAIL_MARKERS = {
    'resentment': {
        'humiliation': ['унижение', 'унижен', 'унижает'],
        'chronic_neglect': ['невнимание', 'игнор', 'не замечают', 'не замечает'],
        'unspoken_conflict': ['невысказан', 'не сказано', 'не проговорено', 'замалч'],
        'loss_of_respect': ['уважение', 'не уважает', 'перестали уважать'],
    },
}

_SELF_DIAGNOSIS_DETAIL_MARKERS = {
    'emotional_flatness': {
        'numbness': ['онемение', 'ничего не чувствую', 'как будто мёртв', 'как будто мертв'],
        'social_disconnection': ['отчуждение', 'от людей', 'ни с кем', 'изоляция'],
        'meaninglessness': ['ничто не имеет веса', 'ничто не важно', 'нет смысла', 'бессмысленно'],
    },
}

_PORTRAIT_DETAIL_MARKERS = {
    'avoidance': {
        'conversation': ['разговор', 'разговора', 'сказать', 'обсуждение'],
        'decision': ['решение', 'решать', 'выбор'],
        'responsibility': ['ответственность', 'обязательство', 'обязанность'],
        'weakness': ['слабость', 'стыд', 'провал'],
    },
}


_ABSTRACTIFY_MARKERS = [
    'абстрактно',
    'в общем виде',
    'в общем',
    'не конкретно у меня',
    'не конкретно',
    'не у меня',
    'не про меня',
]

_PERSONALIZE_MARKERS = [
    'а если у меня',
    'а если у меня лично',
    'если у меня лично',
    'если это у меня',
    'а у меня лично',
    'вернемся ко мне',
    'вернёмся ко мне',
    'а как это у меня',
]

_YES_MARKERS = ['да', 'ага', 'угу', 'именно']

_GREETING_MARKERS = [
    'привет',
    'здравствуйте',
    'добрый вечер',
    'добрый день',
    'доброе утро',
]

_PORTRAIT_MARKERS = [
    'психологический портрет',
    'мой портрет',
    'разбери мой характер',
]

_SELF_DIAGNOSIS_MARKERS = [
    'у меня ангедония',
    'подозреваю, что у меня',
    'кажется, что у меня',
    'похоже, что у меня',
]

_CONVERSATION_FEEDBACK_MARKERS = [
    'ты задаёшь слишком много вопросов',
    'слишком много вопросов',
    'не задавай столько вопросов',
    'меньше вопросов',
]

_MINI_ANALYSIS_MARKERS = [
    'и что это значит',
    'что это значит',
    'ну и что это значит',
    'что это вообще значит',
    'что из этого следует',
    'и что из этого следует',
]

_NEXT_STEP_MARKERS = [
    'и что с этим делать',
    'что с этим делать',
    'ну и что с этим делать',
    'и что теперь делать',
    'что теперь делать',
    'что делать дальше',
    'что дальше делать',
    'какой следующий шаг',
    'и какой следующий шаг',
]

_EXAMPLE_MARKERS = [
    'приведи пример',
    'дай пример',
    'можешь привести пример',
    'а пример',
    'как это выглядит',
    'как это звучит',
]

_CAUSE_LIST_MARKERS = [
    'какие основные причины',
    'основные причины',
    'перечисли причины',
    'назови причины',
    'какие причины',
    'из-за чего это бывает',
    'от чего это бывает',
]

_REJECT_SCOPE_MARKERS = [
    'слишком общо',
    'это слишком общо',
    'слишком широко',
    'это слишком широко',
    'давай конкретнее',
    'можно конкретнее',
    'без общих слов',
    'слишком расплывчато',
]

_TOPIC_SHIFT_MARKERS = [
    'другой вопрос',
    'другая тема',
    'ладно, другой вопрос',
    'ладно другой вопрос',
    'а теперь другой вопрос',
    'теперь другой вопрос',
    'давай теперь про',
    'а теперь про',
    'теперь про',
]

_TOPIC_OPENING_PREFIXES = [
    'какие ',
    'почему ',
    'что ',
    'как ',
    'зачем ',
    'от чего ',
    'из-за чего ',
    'можно ли ',
    'о чем ',
    'о чём ',
    'давайте ',
    'расскажи ',
]


def _normalize(text: str) -> str:
    return ' '.join((text or '').lower().split())


def _contains_any(text: str, markers: list[str]) -> bool:
    return any(marker in text for marker in markers)


def _looks_like_greeting(text: str) -> bool:
    if not text:
        return False
    words = text.split()
    return len(words) <= 6 and _contains_any(text, _GREETING_MARKERS)


def _looks_like_fresh_topic_opening(text: str) -> bool:
    if not text:
        return False
    if len(text.split()) < 4:
        return False
    if any(text.startswith(prefix) for prefix in _TOPIC_OPENING_PREFIXES):
        return True
    return text.endswith('?')


def _match_axis(text: str, mapping: dict[str, list[str]]) -> str:
    for axis, markers in mapping.items():
        if _contains_any(text, markers):
            return axis
    return ''


def _match_nested_detail(text: str, mapping: dict[str, dict[str, list[str]]], axis: str) -> str:
    detail_map = mapping.get(axis, {})
    for detail, markers in detail_map.items():
        if _contains_any(text, markers):
            return detail
    return ''


def extract_dialogue_axis(question: str, state: dict | None = None) -> str:
    """Return a canonical axis when the turn answers an earlier narrowing."""
    state = state or {}
    q = _normalize(question)
    topic = state.get('active_topic', '')
    pending = state.get('pending_slot', '')
    if not q or not topic or not pending:
        return ''

    if topic in {'relationship-loss-of-feeling', 'relationship-foundations'} and pending in {'pattern_family', 'narrowing_axis'}:
        return _match_axis(q, _RELATIONSHIP_AXIS_MARKERS)
    if topic == 'shame-self-contempt' and pending == 'narrowing_axis':
        return _match_axis(q, _SHAME_AXIS_MARKERS)
    if topic == 'self-diagnosis' and pending == 'symptom_narrowing':
        return _match_axis(q, _SELF_DIAGNOSIS_AXIS_MARKERS)
    if topic in {'psychological-portrait', 'self-evaluation'} and pending == 'pattern_selection':
        return _match_axis(q, _PORTRAIT_AXIS_MARKERS)
    return ''


def extract_dialogue_detail(question: str, state: dict | None = None) -> str:
    """Return a detail when the turn answers an axis-specific follow-up."""
    state = state or {}
    q = _normalize(question)
    topic = state.get('active_topic', '')
    pending = state.get('pending_slot', '')
    axis = state.get('active_axis', '')
    if not q or not topic or pending != 'concrete_manifestation' or not axis:
        return ''

    if topic in {'relationship-loss-of-feeling', 'relationship-foundations'}:
        return _match_nested_detail(q, _RELATIONSHIP_DETAIL_MARKERS, axis)
    if topic == 'self-diagnosis':
        return _match_nested_detail(q, _SELF_DIAGNOSIS_DETAIL_MARKERS, axis)
    if topic in {'psychological-portrait', 'self-evaluation'}:
        return _match_nested_detail(q, _PORTRAIT_DETAIL_MARKERS, axis)
    return ''


def infer_dialogue_act(question: str, state: dict | None = None) -> str:
    """Return the current dialogue act for a new turn."""
    state = state or {}
    q = _normalize(question)

    if not q:
        return 'empty_turn'

    if is_scope_menu_question(q):
        return 'request_menu'

    if _looks_like_greeting(q):
        return 'greeting_opening'

    if state.get('active_topic') and _contains_any(q, _TOPIC_SHIFT_MARKERS):
        return 'topic_shift'

    if _contains_any(q, _PORTRAIT_MARKERS):
        return 'request_psychological_portrait'

    if _contains_any(q, _SELF_DIAGNOSIS_MARKERS):
        return 'self_diagnosis_soft'

    if _contains_any(q, _CONVERSATION_FEEDBACK_MARKERS):
        return 'request_conversation_feedback'

    if (
        state.get('active_topic')
        and state.get('dialogue_mode') in {'mini_analysis', 'practical_next_step', 'cause_list'}
        and _contains_any(q, _EXAMPLE_MARKERS)
    ):
        return 'request_example'

    if state.get('active_topic') and _contains_any(q, _CAUSE_LIST_MARKERS):
        return 'request_cause_list'

    if state.get('active_topic') and _contains_any(q, _REJECT_SCOPE_MARKERS):
        return 'reject_scope'

    if (
        state.get('active_topic')
        and (
            state.get('pending_slot') == 'next_step'
            or state.get('dialogue_mode') == 'cause_list'
        )
        and _contains_any(q, _NEXT_STEP_MARKERS)
    ):
        return 'request_next_step'

    if state.get('active_topic') and state.get('pending_slot') == 'analysis_focus' and _contains_any(q, _MINI_ANALYSIS_MARKERS):
        return 'request_mini_analysis'

    if extract_dialogue_detail(q, state):
        return 'supply_concrete_manifestation'

    if extract_dialogue_axis(q, state):
        return 'supply_narrowing_axis'

    if state.get('active_topic') and ('да' in q) and _contains_any(q, ['в общем', 'в общем виде']):
        return 'confirm_scope'

    if state.get('active_topic') and any(marker == q for marker in _YES_MARKERS):
        return 'confirm_previous_question'

    if state.get('active_topic') and _contains_any(q, _PERSONALIZE_MARKERS):
        return 'personalize_previous_question'

    if state.get('active_topic') and _looks_like_fresh_topic_opening(q):
        return 'open_topic'

    if _contains_any(q, _ABSTRACTIFY_MARKERS):
        return 'abstractify_previous_question' if state.get('active_topic') else 'request_generalization'

    return 'open_topic'
