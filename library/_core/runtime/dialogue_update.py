"""Heuristic-first dialogue-frame updates for migration away from rigid acts."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from library._core.runtime.dialogue_family_registry import (
    dialogue_contains_any,
    get_dialogue_family_spec,
    infer_dialogue_family,
    is_dialogue_transition_allowed,
    normalize_dialogue_text,
)
from library._core.runtime.dialogue_frame import DialogueFrame, coerce_frame, infer_frame_type, relation_from_act
from library._core.runtime.dialogue_intent_registry import infer_dialogue_intent
from library._core.runtime.dialogue_intent_registry import question_has_dialogue_intent_marker
from library._core.runtime.dialogue_acts import extract_dialogue_axis, extract_dialogue_detail
from library._core.runtime.routes import infer_route
from library._core.runtime.dialogue_state import DialogueState
from library._core.runtime.dialogue_state import infer_active_topic


@dataclass
class DialogueUpdate:
    relation_to_previous: str = 'new'
    is_new_topic: bool = False
    topic_candidate: str = ''
    route_candidate: str = ''
    frame_type_candidate: str = ''
    stance_shift: str = ''
    goal_candidate: str = ''
    transition_kind: str = ''
    slot_fill: dict = field(default_factory=dict)
    confidence: float = 0.0
    update_source: str = ''

    def as_dict(self) -> dict:
        return asdict(self)


def _normalize(text: str) -> str:
    return normalize_dialogue_text(text)


def _contains_any(text: str, markers: list[str]) -> bool:
    return dialogue_contains_any(text, markers)


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
    'в чем ',
    'в чём ',
    'из чего ',
    'на чем ',
    'на чём ',
]

_SLOT_FOLLOWUP_PREFIXES = [
    'скорее ',
    'скорее, ',
    'больше ',
    'главнее ',
    'прежде всего ',
    'скорее из ',
    'скорее от ',
]


def _looks_like_fresh_topic_opening(text: str) -> bool:
    if not text:
        return False
    if question_has_dialogue_intent_marker(text):
        return False
    if len(text.split()) < 4:
        return False
    if any(text.startswith(prefix) for prefix in _TOPIC_OPENING_PREFIXES):
        return True
    return text.endswith('?')


def _looks_like_slot_followup_candidate(text: str) -> bool:
    if not text:
        return False
    if any(text.startswith(prefix) for prefix in _SLOT_FOLLOWUP_PREFIXES):
        return True
    return len(text.split()) <= 4 and text.startswith('из ')


def _family_stance_goal(topic: str) -> tuple[str, str]:
    spec = get_dialogue_family_spec(topic)
    if spec is None:
        return '', ''
    return spec.stance, spec.goal


def _transition_kind_for_act(dialogue_act: str) -> str:
    return {
        'abstractify_previous_question': 'reframe_general',
        'confirm_scope': 'reframe_general',
        'personalize_previous_question': 'reframe_personal',
        'reject_scope': 'reject_scope',
        'request_cause_list': 'cause_list',
        'request_example': 'example',
        'request_next_step': 'next_step',
        'request_mini_analysis': 'mini_analysis',
        'supply_narrowing_axis': 'axis_answer',
        'supply_concrete_manifestation': 'detail_answer',
        'topic_shift': 'topic_shift',
    }.get(dialogue_act, 'opening')


def _family_opening_pending_slot(topic: str) -> str:
    spec = get_dialogue_family_spec(topic)
    if spec is None:
        return ''
    return spec.opening_pending_slot


def _infer_special_topic(question: str, dialogue_act: str) -> tuple[str, str]:
    semantic_family = infer_dialogue_family(question)
    if semantic_family:
        return (
            semantic_family.get('topic_candidate', '') or '',
            semantic_family.get('route_candidate', '') or '',
        )
    return '', ''


def _build_update_payload(*,
                          relation_to_previous: str,
                          is_new_topic: bool,
                          topic_candidate: str,
                          route_candidate: str,
                          stance_shift: str,
                          goal_candidate: str,
                          transition_kind: str,
                          pending_slot: str,
                          confidence: float,
                          update_source: str,
                          axis: str = '',
                          detail: str = '') -> dict:
    return {
        'relation_to_previous': relation_to_previous,
        'is_new_topic': is_new_topic,
        'topic_candidate': topic_candidate,
        'route_candidate': route_candidate,
        'stance_shift': stance_shift,
        'goal_candidate': goal_candidate,
        'transition_kind': transition_kind,
        'slot_fill': {'axis': axis, 'detail': detail, 'pending_slot': pending_slot},
        'confidence': confidence,
        'update_source': update_source,
    }


def _infer_update_from_question(question: str, *,
                                state: dict,
                                frame: DialogueFrame,
                                selected_axis: str = '',
                                selected_detail: str = '') -> dict:
    q = _normalize(question)
    if not q:
        return {}

    active_topic = frame.topic or state.get('active_topic', '')
    previous_pending_slot = state.get('pending_slot', '') or frame.pending_slot

    if _contains_any(q, _TOPIC_SHIFT_MARKERS):
        special_topic, special_route = _infer_special_topic(question, 'topic_shift')
        topic_candidate = special_topic or infer_active_topic(question, route_name='') or active_topic
        stance_shift, goal_candidate = _family_stance_goal(topic_candidate)
        return _build_update_payload(
            relation_to_previous='shift',
            is_new_topic=True,
            topic_candidate=topic_candidate,
            route_candidate=special_route or frame.route or state.get('active_route', ''),
            stance_shift=stance_shift or ('general' if topic_candidate in {'scope-topics', 'relationship-foundations', 'greeting'} else 'personal'),
            goal_candidate=goal_candidate or 'clarify',
            transition_kind='opening',
            pending_slot=_family_opening_pending_slot(topic_candidate),
            confidence=0.93,
            update_source='intent_registry',
        )

    slotish_followup = bool(active_topic) and _looks_like_slot_followup_candidate(q) and not _looks_like_fresh_topic_opening(q)
    semantic_family = None if slotish_followup else infer_dialogue_family(question)

    if semantic_family:
        return _build_update_payload(
            relation_to_previous='new',
            is_new_topic=True,
            topic_candidate=semantic_family.get('topic_candidate', ''),
            route_candidate=semantic_family.get('route_candidate', ''),
            stance_shift=semantic_family.get('stance_shift', ''),
            goal_candidate=semantic_family.get('goal_candidate', ''),
            transition_kind='opening',
            pending_slot=_family_opening_pending_slot(semantic_family.get('topic_candidate', '')),
            confidence=float(semantic_family.get('confidence', 0.78) or 0.78),
            update_source='family_registry',
        )

    if active_topic and _looks_like_fresh_topic_opening(q):
        route_guess = infer_route(question)
        topic_guess = infer_active_topic(question, route_name=route_guess) or route_guess
        if topic_guess and topic_guess not in {'', active_topic, 'general'}:
            stance_guess, goal_guess = _family_stance_goal(topic_guess)
            return _build_update_payload(
                relation_to_previous='shift',
                is_new_topic=True,
                topic_candidate=topic_guess,
                route_candidate=route_guess if route_guess != 'general' or topic_guess == 'scope-topics' else frame.route or state.get('active_route', ''),
                stance_shift=stance_guess or ('general' if topic_guess in {'scope-topics', 'relationship-foundations', 'greeting'} else 'personal'),
                goal_candidate=goal_guess or 'clarify',
                transition_kind='opening',
                pending_slot=_family_opening_pending_slot(topic_guess),
                confidence=0.89,
                update_source='fresh_topic_guard',
            )

    inferred_axis = selected_axis or extract_dialogue_axis(question, state)
    if active_topic and inferred_axis and is_dialogue_transition_allowed(
        active_topic,
        'axis_answer',
        goal=frame.goal,
        dialogue_mode=state.get('dialogue_mode', ''),
        pending_slot=previous_pending_slot,
        abstraction_level=state.get('abstraction_level', ''),
    ):
        return _build_update_payload(
            relation_to_previous='answer_slot',
            is_new_topic=False,
            topic_candidate=active_topic,
            route_candidate=frame.route or state.get('active_route', ''),
            stance_shift='',
            goal_candidate='clarify',
            transition_kind='axis_answer',
            pending_slot=previous_pending_slot,
            confidence=0.9,
            update_source='slot_answer',
            axis=inferred_axis,
        )

    inferred_detail = selected_detail or extract_dialogue_detail(question, state)
    if active_topic and inferred_detail and is_dialogue_transition_allowed(
        active_topic,
        'detail_answer',
        goal=frame.goal,
        dialogue_mode=state.get('dialogue_mode', ''),
        pending_slot=previous_pending_slot,
        abstraction_level=state.get('abstraction_level', ''),
    ):
        return _build_update_payload(
            relation_to_previous='answer_slot',
            is_new_topic=False,
            topic_candidate=active_topic,
            route_candidate=frame.route or state.get('active_route', ''),
            stance_shift='',
            goal_candidate='clarify',
            transition_kind='detail_answer',
            pending_slot=previous_pending_slot,
            confidence=0.9,
            update_source='slot_answer',
            axis=state.get('active_axis', ''),
            detail=inferred_detail,
        )

    intent_spec = infer_dialogue_intent(question, active_topic=active_topic)
    if active_topic and intent_spec and intent_spec.name != 'topic_shift':
        return _build_update_payload(
            relation_to_previous=intent_spec.relation,
            is_new_topic=False,
            topic_candidate=active_topic,
            route_candidate=frame.route or state.get('active_route', ''),
            stance_shift=intent_spec.stance_shift,
            goal_candidate=intent_spec.goal,
            transition_kind=_transition_kind_for_act(intent_spec.name),
            pending_slot=previous_pending_slot,
            confidence=intent_spec.confidence,
            update_source='intent_registry',
        )

    return {}


def _default_stance_for_act(dialogue_act: str, topic_candidate: str = '') -> str:
    if dialogue_act in {'request_menu', 'greeting_opening'}:
        return 'general'
    if dialogue_act in {
        'open_topic',
        'topic_shift',
        'request_psychological_portrait',
        'self_diagnosis_soft',
    }:
        return 'personal'
    if topic_candidate in {'psychological-portrait', 'self-diagnosis', 'relationship-loss-of-feeling'}:
        return 'personal'
    return ''


def _default_goal_for_act(dialogue_act: str, topic_candidate: str = '') -> str:
    if dialogue_act == 'greeting_opening':
        return 'opening'
    if dialogue_act == 'request_menu':
        return 'menu'
    if dialogue_act in {'request_psychological_portrait', 'self_diagnosis_soft'}:
        return 'clarify'
    if dialogue_act == 'topic_shift':
        if topic_candidate in {'psychological-portrait', 'self-diagnosis'}:
            return 'clarify'
        if topic_candidate in {'scope-topics', 'greeting'}:
            return 'menu' if topic_candidate == 'scope-topics' else 'opening'
        return 'opening'
    if dialogue_act == 'open_topic':
        return 'opening'
    return ''


def infer_dialogue_update(question: str, *,
                          dialogue_act: str,
                          dialogue_state: dict | None = None,
                          dialogue_frame: dict | DialogueFrame | None = None,
                          selected_axis: str = '',
                          selected_detail: str = '') -> DialogueUpdate:
    if isinstance(dialogue_state, DialogueState):
        state = dialogue_state.as_dict()
    else:
        state = dict(dialogue_state or {})
    frame = coerce_frame(dialogue_frame)
    relation = relation_from_act(dialogue_act)
    topic_candidate = frame.topic
    route_candidate = frame.route
    stance_shift = ''
    goal_candidate = ''
    transition_kind = _transition_kind_for_act(dialogue_act)
    is_new_topic = False
    confidence = 0.55
    update_source = 'dialogue_act_fallback'

    direct_update = _infer_update_from_question(
        question,
        state=state,
        frame=frame,
        selected_axis=selected_axis,
        selected_detail=selected_detail,
    )
    if direct_update:
        return DialogueUpdate(
            relation_to_previous=direct_update.get('relation_to_previous', relation),
            is_new_topic=bool(direct_update.get('is_new_topic', False)),
            topic_candidate=direct_update.get('topic_candidate', topic_candidate),
            route_candidate=direct_update.get('route_candidate', route_candidate),
            frame_type_candidate='',
            stance_shift=direct_update.get('stance_shift', ''),
            goal_candidate=direct_update.get('goal_candidate', ''),
            transition_kind=direct_update.get('transition_kind', ''),
            slot_fill=dict(direct_update.get('slot_fill') or {}),
            confidence=float(direct_update.get('confidence', 0.0) or 0.0),
            update_source=direct_update.get('update_source', ''),
        )

    if dialogue_act in {'open_topic', 'greeting_opening', 'request_menu', 'request_psychological_portrait', 'self_diagnosis_soft'}:
        semantic_family = infer_dialogue_family(question)
        if semantic_family:
            topic_candidate = semantic_family.get('topic_candidate', '') or topic_candidate
            route_candidate = semantic_family.get('route_candidate', '') or route_candidate
            stance_shift = semantic_family.get('stance_shift', '') or stance_shift
            goal_candidate = semantic_family.get('goal_candidate', '') or goal_candidate
        else:
            topic_candidate = infer_active_topic(question, route_name=state.get('active_route', '') or frame.route)
            route_candidate = state.get('active_route', '') or frame.route
        is_new_topic = True
        confidence = 0.82
    elif dialogue_act == 'topic_shift':
        semantic_family = infer_dialogue_family(question)
        if semantic_family:
            topic_candidate = semantic_family.get('topic_candidate', '') or topic_candidate
            route_candidate = semantic_family.get('route_candidate', '') or route_candidate
            stance_shift = semantic_family.get('stance_shift', '') or stance_shift
            goal_candidate = semantic_family.get('goal_candidate', '') or goal_candidate
        else:
            topic_candidate = infer_active_topic(question, route_name='') or topic_candidate
            route_candidate = frame.route
        is_new_topic = True
        confidence = 0.9
    if is_new_topic:
        family_stance, family_goal = _family_stance_goal(topic_candidate)
        stance_shift = family_stance or _default_stance_for_act(dialogue_act, topic_candidate) or stance_shift
        goal_candidate = family_goal or _default_goal_for_act(dialogue_act, topic_candidate) or goal_candidate
    if dialogue_act in {'abstractify_previous_question', 'confirm_scope', 'request_generalization'}:
        stance_shift = 'general'
        goal_candidate = 'overview'
        confidence = 0.9
    elif dialogue_act in {'personalize_previous_question', 'reject_scope'}:
        stance_shift = 'personal'
        goal_candidate = 'clarify'
        confidence = 0.9
    elif dialogue_act == 'request_cause_list':
        goal_candidate = 'cause_list'
        confidence = 0.9
    elif dialogue_act == 'request_example':
        goal_candidate = 'example'
        confidence = 0.9
    elif dialogue_act == 'request_next_step':
        goal_candidate = 'next_step'
        confidence = 0.9
    elif dialogue_act == 'request_mini_analysis':
        goal_candidate = 'mini_analysis'
        confidence = 0.9
    elif dialogue_act in {'supply_narrowing_axis', 'supply_concrete_manifestation'}:
        goal_candidate = 'clarify'
        confidence = 0.88

    return DialogueUpdate(
        relation_to_previous=relation,
        is_new_topic=is_new_topic,
        topic_candidate=topic_candidate,
        route_candidate=route_candidate,
        frame_type_candidate='',
        stance_shift=stance_shift,
        goal_candidate=goal_candidate,
        transition_kind=transition_kind,
        slot_fill={
            'axis': selected_axis,
            'detail': selected_detail,
            'pending_slot': state.get('pending_slot', '') or frame.pending_slot,
        },
        confidence=confidence,
        update_source=update_source,
    )


def apply_dialogue_update(current_frame: dict | DialogueFrame | None,
                          update: dict | DialogueUpdate | None,
                          *,
                          fallback_state: dict | None = None) -> DialogueFrame:
    frame = coerce_frame(current_frame)
    if isinstance(update, DialogueUpdate):
        payload = update.as_dict()
    else:
        payload = dict(update or {})
    if isinstance(fallback_state, DialogueState):
        state = fallback_state.as_dict()
    else:
        state = dict(fallback_state or {})

    if payload.get('is_new_topic'):
        frame.topic = payload.get('topic_candidate', '') or frame.topic
        frame.route = payload.get('route_candidate', '') or state.get('active_route', '') or frame.route
        frame.frame_type = ''
        frame.axis = ''
        frame.detail = ''
        frame.pending_slot = ''
    if payload.get('stance_shift'):
        frame.stance = payload.get('stance_shift') or frame.stance
    elif payload.get('is_new_topic'):
        frame.stance = 'personal'
    if payload.get('goal_candidate'):
        frame.goal = payload.get('goal_candidate') or frame.goal
    elif payload.get('is_new_topic'):
        frame.goal = 'opening'
    frame.relation_to_previous = payload.get('relation_to_previous', '') or frame.relation_to_previous
    frame.transition_kind = payload.get('transition_kind', '') or frame.transition_kind
    slot_fill = dict(payload.get('slot_fill') or {})
    frame.axis = slot_fill.get('axis', '') or frame.axis
    frame.detail = slot_fill.get('detail', '') or frame.detail
    frame.pending_slot = slot_fill.get('pending_slot', '') or state.get('pending_slot', '') or frame.pending_slot
    frame.confidence = str(payload.get('confidence', frame.confidence) or frame.confidence)
    frame.update_source = payload.get('update_source', '') or frame.update_source

    if not frame.topic:
        frame.topic = state.get('active_topic', '') or ''
    if not frame.route:
        frame.route = state.get('active_route', '') or ''
    if not frame.frame_type:
        frame.frame_type = infer_frame_type(frame.topic, frame.stance)
    return frame
