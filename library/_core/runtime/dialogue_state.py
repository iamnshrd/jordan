"""Dialogue-state transitions for short-horizon conversational continuity."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from library._core.runtime.dialogue_family_registry import (
    get_dialogue_family_spec,
    get_dialogue_transition_hints,
    infer_dialogue_family,
    is_dialogue_transition_allowed,
    resolve_dialogue_transition,
)
from library.utils import now_iso


_RELATIONSHIP_LOSS_MARKERS = [
    'потери чувств',
    'потеря чувств',
    'потерял чувства',
    'потеряла чувства',
    'разлюбил',
    'разлюбила',
    'чувства прошли',
    'прошли чувства',
]

_LOST_AND_AIMLESS_MARKERS = [
    'я потерялся',
    'я потерялас',
    'потерял смысл',
    'потеряла смысл',
    'потерял направление',
    'потеряла направление',
    'потерял смысл и направление',
    'потеряла смысл и направление',
    'нет смысла и направления',
    'нет смысла',
    'не понимаю куда идти',
    'не понимаю что делать дальше',
]

_SCOPE_MENU_MARKERS = [
    'о чем можно поговорить',
    'о чём можно поговорить',
    'о чем с тобой можно поговорить',
    'о чём с тобой можно поговорить',
    'какие темы ты разбираешь',
    'какие темы можно разобрать',
    'что мы можем обсудить',
    'что можно обсудить',
    'с тобой можно обсудить',
    'на какие темы с тобой можно говорить',
    'какие вопросы ты разбираешь',
]

_SCOPE_MENU_CONCEPT_MARKERS = [
    'о чем',
    'о чём',
    'какие темы',
    'какие вопросы',
    'что можно',
    'что мы можем',
    'на какие темы',
]

_SCOPE_MENU_SUBJECT_MARKERS = [
    'поговорить',
    'обсудить',
    'разобрать',
    'говорить',
]

_SCOPE_MENU_PARTNER_MARKERS = [
    'с тобой',
    'ты',
    'у тебя',
]

_SELF_EVALUATION_MARKERS = [
    'что со мной не так',
    'что со мнои не так',
    'почему я всё порчу',
    'почему я все порчу',
    'почему я всё ломаю',
    'почему я все ломаю',
    'кто я такой',
    'кто я такая',
    'какой я человек',
    'что я за человек',
    'почему я такой',
    'почему я такая',
]

_SELF_EVALUATION_CONCEPT_MARKERS = [
    'что со мной',
    'почему я',
    'кто я',
    'какой я',
    'что я за',
]

_SELF_EVALUATION_SUBJECT_MARKERS = [
    'не так',
    'порчу',
    'ломаю',
    'человек',
    'такой',
    'такая',
]

_SHAME_SELF_CONTEMPT_MARKERS = [
    'мне стыдно за себя',
    'стыдно за себя',
    'я себя ненавижу',
    'ненавижу себя',
    'отвращение к себе',
    'я ничтожество',
    'я никчемный',
    'я никчёмный',
    'я никчемная',
    'я никчёмная',
    'мне за себя противно',
    'я мерзок себе',
    'я мерзка себе',
    'мне за себя позорно',
]

_SHAME_SELF_CONTEMPT_CONCEPT_MARKERS = [
    'стыдно',
    'ненавижу',
    'отвращение',
    'позорно',
    'мерзок',
    'мерзка',
    'ничтож',
    'никчем',
    'никчём',
]

_SHAME_SELF_CONTEMPT_SELF_MARKERS = [
    'за себя',
    'себя',
    'себе',
    'я ',
]

_RELATIONSHIP_FOUNDATIONS_MARKERS = [
    'смысл крепких отношений',
    'суть крепких отношений',
    'крепких отношений',
    'крепкие отношения',
    'сильных отношений',
    'суть отношений',
    'смысл отношений',
    'основа отношений',
    'здоровые отношения',
]

_RELATIONSHIP_FOUNDATION_CONCEPT_MARKERS = [
    'в чем заключается',
    'в чём заключается',
    'в чем смысл',
    'в чём смысл',
    'в чем суть',
    'в чём суть',
    'в чем основа',
    'в чём основа',
    'что делает',
    'что удерживает',
    'на чем держ',
    'на чём держ',
]

_RELATIONSHIP_FOUNDATION_SUBJECT_MARKERS = [
    'отношени',
    'брак',
    'брака',
    'браке',
    'союз',
    'пара',
    'семь',
]


def _normalize(text: str) -> str:
    return ' '.join((text or '').lower().split())


def _contains_any(text: str, markers: list[str]) -> bool:
    return any(marker in text for marker in markers)


def is_relationship_foundations_question(question: str) -> bool:
    q = _normalize(question)
    if not q:
        return False
    if _contains_any(q, _RELATIONSHIP_FOUNDATIONS_MARKERS):
        return True
    return (
        _contains_any(q, _RELATIONSHIP_FOUNDATION_CONCEPT_MARKERS)
        and _contains_any(q, _RELATIONSHIP_FOUNDATION_SUBJECT_MARKERS)
    )


def is_lost_and_aimless_question(question: str) -> bool:
    q = _normalize(question)
    if not q:
        return False
    return _contains_any(q, _LOST_AND_AIMLESS_MARKERS)


def is_scope_menu_question(question: str) -> bool:
    q = _normalize(question)
    if not q:
        return False
    if _contains_any(q, _SCOPE_MENU_MARKERS):
        return True
    return (
        _contains_any(q, _SCOPE_MENU_CONCEPT_MARKERS)
        and _contains_any(q, _SCOPE_MENU_SUBJECT_MARKERS)
        and _contains_any(q, _SCOPE_MENU_PARTNER_MARKERS)
    )


def is_self_evaluation_question(question: str) -> bool:
    q = _normalize(question)
    if not q:
        return False
    if _contains_any(q, _SELF_EVALUATION_MARKERS):
        return True
    return (
        _contains_any(q, _SELF_EVALUATION_CONCEPT_MARKERS)
        and _contains_any(q, _SELF_EVALUATION_SUBJECT_MARKERS)
    )


def is_shame_self_contempt_question(question: str) -> bool:
    q = _normalize(question)
    if not q:
        return False
    if _contains_any(q, _SHAME_SELF_CONTEMPT_MARKERS):
        return True
    return (
        _contains_any(q, _SHAME_SELF_CONTEMPT_CONCEPT_MARKERS)
        and _contains_any(q, _SHAME_SELF_CONTEMPT_SELF_MARKERS)
    )


@dataclass
class DialogueState:
    version: int = 1
    active_topic: str = ''
    active_route: str = ''
    active_problem_frame: str = ''
    dialogue_mode: str = 'topic_opening'
    abstraction_level: str = 'personal'
    pending_slot: str = ''
    last_clarify_profile: str = ''
    last_question_kind: str = ''
    last_reason_code: str = ''
    last_user_turn: str = ''
    last_system_turn: str = ''
    last_turn_at: str = ''
    turn_count_in_topic: int = 0
    topic_confidence: str = ''
    candidate_axes: list[str] = field(default_factory=list)
    active_axis: str = ''
    active_detail: str = ''

    def as_dict(self) -> dict:
        return asdict(self)


def coerce_state(data: dict | None) -> DialogueState:
    payload = dict(data or {})
    return DialogueState(
        version=int(payload.get('version', 1) or 1),
        active_topic=payload.get('active_topic', '') or '',
        active_route=payload.get('active_route', '') or '',
        active_problem_frame=payload.get('active_problem_frame', '') or '',
        dialogue_mode=payload.get('dialogue_mode', 'topic_opening') or 'topic_opening',
        abstraction_level=payload.get('abstraction_level', 'personal') or 'personal',
        pending_slot=payload.get('pending_slot', '') or '',
        last_clarify_profile=payload.get('last_clarify_profile', '') or '',
        last_question_kind=payload.get('last_question_kind', '') or '',
        last_reason_code=payload.get('last_reason_code', '') or '',
        last_user_turn=payload.get('last_user_turn', '') or '',
        last_system_turn=payload.get('last_system_turn', '') or '',
        last_turn_at=payload.get('last_turn_at', '') or '',
        turn_count_in_topic=int(payload.get('turn_count_in_topic', 0) or 0),
        topic_confidence=payload.get('topic_confidence', '') or '',
        candidate_axes=list(payload.get('candidate_axes') or []),
        active_axis=payload.get('active_axis', '') or '',
        active_detail=payload.get('active_detail', '') or '',
    )


def infer_active_topic(question: str, *, route_name: str = '',
                       clarify_profile: str = '') -> str:
    q = _normalize(question)
    if clarify_profile:
        if clarify_profile == 'greeting-opening':
            return 'greeting'
        if clarify_profile == 'psychological-portrait-request':
            return 'psychological-portrait'
        if clarify_profile == 'self-diagnosis-soft':
            return 'self-diagnosis'
        if clarify_profile == 'self-evaluation-request':
            return 'self-evaluation'
        if clarify_profile == 'shame-self-contempt-request':
            return 'shame-self-contempt'
        if clarify_profile == 'scope-topics':
            return 'scope-topics'
        if clarify_profile == 'conversation-feedback':
            return 'conversation-feedback'
    semantic_family = infer_dialogue_family(q)
    if semantic_family:
        return semantic_family.get('topic_candidate', '') or ''
    if route_name == 'relationship-maintenance':
        if is_relationship_foundations_question(q):
            return 'relationship-foundations'
        if _contains_any(q, _RELATIONSHIP_LOSS_MARKERS):
            return 'relationship-loss-of-feeling'
        return 'relationship-knot'
    if route_name == 'career-vocation' and is_lost_and_aimless_question(q):
        return 'lost-and-aimless'
    if route_name == 'shame-self-contempt' and is_shame_self_contempt_question(q):
        return 'shame-self-contempt'
    if route_name == 'general' and is_scope_menu_question(q):
        return 'scope-topics'
    if route_name == 'general' and is_self_evaluation_question(q):
        return 'self-evaluation'
    return route_name or ''


def advance_dialogue_state(current_state: dict | None, *, question: str,
                           dialogue_act: str, route_name: str = '',
                           clarify_profile: str = '',
                           reason_code: str = '',
                           decision_type: str = '',
                           final_user_text: str = '',
                           question_kind: str = '',
                           confidence: str = '',
                           selected_axis: str = '',
                           selected_detail: str = '') -> DialogueState:
    state = coerce_state(current_state)
    next_state = coerce_state(state.as_dict())
    now = now_iso()
    transition_kind = {
        'abstractify_previous_question': 'reframe_general',
        'confirm_scope': 'reframe_general',
        'personalize_previous_question': 'reframe_personal',
        'supply_narrowing_axis': 'axis_answer',
        'supply_concrete_manifestation': 'detail_answer',
        'request_mini_analysis': 'mini_analysis',
        'request_next_step': 'next_step',
        'request_example': 'example',
        'request_cause_list': 'cause_list',
        'reject_scope': 'reject_scope',
    }.get(dialogue_act, '')

    transition_result = {}
    if transition_kind and state.active_topic:
        transition_result = resolve_dialogue_transition(
            state.active_topic,
            transition_kind,
            dialogue_mode=state.dialogue_mode,
            pending_slot=state.pending_slot,
            abstraction_level=state.abstraction_level,
        )

    if transition_kind and state.active_topic and not transition_result:
        next_state.last_user_turn = question or ''
        next_state.last_system_turn = final_user_text or ''
        next_state.last_turn_at = now
        next_state.topic_confidence = confidence or state.topic_confidence
        if selected_axis:
            next_state.active_axis = selected_axis
        if selected_detail:
            next_state.active_detail = selected_detail
        family_spec = get_dialogue_family_spec(next_state.active_topic)
        if family_spec and family_spec.candidate_axes:
            next_state.candidate_axes = list(family_spec.candidate_axes)
        return next_state

    if transition_result:
        next_state.dialogue_mode = transition_result.get('dialogue_mode', state.dialogue_mode)
        next_state.abstraction_level = transition_result.get('stance', state.abstraction_level) or state.abstraction_level or 'personal'
        next_state.pending_slot = transition_result.get('pending_slot', state.pending_slot)
        next_state.turn_count_in_topic = max(1, state.turn_count_in_topic) + 1
        next_state.active_axis = '' if transition_result.get('clear_axis') else state.active_axis
        next_state.active_detail = '' if transition_result.get('clear_detail') else state.active_detail
        if transition_kind == 'axis_answer':
            next_state.active_axis = selected_axis or state.active_axis
        if transition_kind == 'detail_answer':
            next_state.active_detail = selected_detail or state.active_detail
    else:
        active_topic = infer_active_topic(
            question,
            route_name=route_name or state.active_route,
            clarify_profile=clarify_profile,
        )
        if active_topic:
            family_spec = get_dialogue_family_spec(active_topic)
            if active_topic == state.active_topic:
                next_state.turn_count_in_topic = max(1, state.turn_count_in_topic) + 1
            else:
                next_state.turn_count_in_topic = 1
            next_state.active_topic = active_topic
            next_state.active_route = route_name or state.active_route
            next_state.active_problem_frame = clarify_profile or state.active_problem_frame
            next_state.abstraction_level = 'personal'
            next_state.active_axis = ''
            next_state.active_detail = ''
            if dialogue_act in ('request_generalization',):
                next_state.abstraction_level = 'general'
            if dialogue_act == 'request_menu':
                next_state.dialogue_mode = 'scope_clarify'
                next_state.pending_slot = 'topic_selection'
            elif dialogue_act == 'greeting_opening' or clarify_profile == 'greeting-opening':
                next_state.dialogue_mode = 'topic_opening'
                next_state.pending_slot = ''
            elif family_spec and (
                dialogue_act in {'request_psychological_portrait', 'self_diagnosis_soft'}
                or clarify_profile in {
                    'psychological-portrait-request',
                    'self-diagnosis-soft',
                    'self-evaluation-request',
                    'shame-self-contempt-request',
                    'lost-and-aimless',
                    'relationship-foundations-overview',
                    'relationship-knot',
                }
                or decision_type == 'clarify'
            ):
                opening_transition = resolve_dialogue_transition(active_topic, 'opening')
                next_state.dialogue_mode = opening_transition.get('dialogue_mode', family_spec.opening_mode)
                next_state.pending_slot = opening_transition.get('pending_slot', family_spec.opening_pending_slot)
                next_state.abstraction_level = opening_transition.get('stance', next_state.abstraction_level) or next_state.abstraction_level
            elif decision_type == 'clarify' and clarify_profile:
                next_state.dialogue_mode = 'human_problem_clarify'
                next_state.pending_slot = 'narrowing_axis'
            elif decision_type == 'respond_kb':
                next_state.dialogue_mode = 'kb_answer'
                next_state.pending_slot = ''
            else:
                if family_spec:
                    opening_transition = resolve_dialogue_transition(active_topic, 'opening')
                    next_state.dialogue_mode = opening_transition.get('dialogue_mode', family_spec.opening_mode)
                    next_state.pending_slot = opening_transition.get('pending_slot', family_spec.opening_pending_slot)
                    next_state.abstraction_level = opening_transition.get('stance', next_state.abstraction_level) or next_state.abstraction_level
                else:
                    next_state.dialogue_mode = 'topic_opening'
                    next_state.pending_slot = ''

    next_state.last_clarify_profile = clarify_profile or state.last_clarify_profile
    next_state.last_question_kind = question_kind or state.last_question_kind
    next_state.last_reason_code = reason_code or state.last_reason_code
    next_state.last_user_turn = question or ''
    next_state.last_system_turn = final_user_text or ''
    next_state.last_turn_at = now
    next_state.topic_confidence = confidence or state.topic_confidence
    if selected_axis:
        next_state.active_axis = selected_axis
    if selected_detail:
        next_state.active_detail = selected_detail
    family_spec = get_dialogue_family_spec(next_state.active_topic)
    if family_spec and family_spec.candidate_axes:
        next_state.candidate_axes = list(family_spec.candidate_axes)
    return next_state


def build_dialogue_metadata(state: dict | DialogueState | None, *,
                            dialogue_act: str = '',
                            topic_reused: bool = False) -> dict:
    coerced = state if isinstance(state, DialogueState) else coerce_state(state)
    return {
        'dialogue_act': dialogue_act,
        'dialogue_mode': coerced.dialogue_mode,
        'active_topic': coerced.active_topic,
        'active_route': coerced.active_route,
        'abstraction_level': coerced.abstraction_level,
        'pending_slot': coerced.pending_slot,
        'active_axis': coerced.active_axis,
        'active_detail': coerced.active_detail,
        'topic_reused': bool(topic_reused),
        'turn_count_in_topic': coerced.turn_count_in_topic,
    }
