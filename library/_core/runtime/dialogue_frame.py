"""Dialogue-frame model for adaptive conversational planning."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from library._core.runtime.dialogue_state import DialogueState


_RELATION_MAP = {
    'abstractify_previous_question': 'reframe',
    'confirm_scope': 'continue',
    'personalize_previous_question': 'reframe',
    'request_menu': 'new',
    'greeting_opening': 'new',
    'request_psychological_portrait': 'new',
    'self_diagnosis_soft': 'new',
    'supply_narrowing_axis': 'answer_slot',
    'supply_concrete_manifestation': 'answer_slot',
    'request_mini_analysis': 'continue',
    'request_next_step': 'continue',
    'request_example': 'continue',
    'request_cause_list': 'continue',
    'reject_scope': 'reframe',
    'topic_shift': 'shift',
    'request_generalization': 'reframe',
    'open_topic': 'new',
}

_GOAL_BY_MODE = {
    'topic_opening': 'opening',
    'scope_clarify': 'menu',
    'human_problem_clarify': 'clarify',
    'followup_reframe': 'overview',
    'followup_narrowing': 'clarify',
    'followup_deepen': 'clarify',
    'mini_analysis': 'mini_analysis',
    'practical_next_step': 'next_step',
    'example_illustration': 'example',
    'cause_list': 'cause_list',
    'kb_answer': 'analyze',
}

_MODE_BY_GOAL = {
    'opening': 'topic_opening',
    'menu': 'scope_clarify',
    'clarify': 'human_problem_clarify',
    'overview': 'followup_reframe',
    'mini_analysis': 'mini_analysis',
    'next_step': 'practical_next_step',
    'example': 'example_illustration',
    'cause_list': 'cause_list',
    'analyze': 'kb_answer',
}

_ACT_BY_TRANSITION = {
    'reframe_general': 'abstractify_previous_question',
    'reframe_personal': 'personalize_previous_question',
    'reject_scope': 'reject_scope',
    'axis_answer': 'supply_narrowing_axis',
    'detail_answer': 'supply_concrete_manifestation',
    'mini_analysis': 'request_mini_analysis',
    'next_step': 'request_next_step',
    'example': 'request_example',
    'cause_list': 'request_cause_list',
}


@dataclass
class DialogueFrame:
    version: int = 1
    topic: str = ''
    route: str = ''
    frame_type: str = ''
    stance: str = 'personal'
    goal: str = 'opening'
    axis: str = ''
    detail: str = ''
    pending_slot: str = ''
    relation_to_previous: str = 'new'
    transition_kind: str = ''
    confidence: str = ''
    update_source: str = ''

    def as_dict(self) -> dict:
        return asdict(self)


def infer_frame_type(topic: str, stance: str) -> str:
    if topic == 'relationship-loss-of-feeling':
        return 'relationship_general' if stance == 'general' else 'relationship_problem'
    if topic == 'relationship-foundations':
        return 'relationship_foundations'
    if topic == 'relationship-knot':
        return 'relationship_problem'
    if topic == 'lost-and-aimless':
        return 'meaning_direction'
    if topic == 'psychological-portrait':
        return 'portrait_request'
    if topic == 'self-evaluation':
        return 'self_inquiry'
    if topic == 'shame-self-contempt':
        return 'shame_self_contempt'
    if topic == 'resentment-conflict':
        return 'resentment_conflict'
    if topic == 'self-deception':
        return 'self_deception'
    if topic == 'fear-and-price':
        return 'fear_value'
    if topic == 'loneliness-rejection':
        return 'loneliness_rejection'
    if topic == 'parenting-boundaries':
        return 'parenting_boundaries'
    if topic == 'tragedy-bitterness':
        return 'tragedy_bitterness'
    if topic == 'self-diagnosis':
        return 'self_diagnosis_soft'
    if topic == 'scope-topics':
        return 'scope_menu'
    if topic == 'conversation-feedback':
        return 'conversation_feedback'
    if topic == 'greeting':
        return 'greeting'
    return topic or ''


def relation_from_act(dialogue_act: str) -> str:
    return _RELATION_MAP.get(dialogue_act or '', 'new')


def goal_from_mode(dialogue_mode: str) -> str:
    return _GOAL_BY_MODE.get(dialogue_mode or '', 'opening')


def mode_from_goal(goal: str) -> str:
    return _MODE_BY_GOAL.get(goal or '', 'topic_opening')


def dialogue_act_from_frame(frame: dict | DialogueFrame | None, *, fallback: str = '') -> str:
    coerced = frame if isinstance(frame, DialogueFrame) else coerce_frame(frame)
    transition_kind = coerced.transition_kind or ''
    if transition_kind == 'opening':
        if coerced.relation_to_previous == 'shift':
            return 'topic_shift'
        if coerced.topic == 'scope-topics':
            return 'request_menu'
        if coerced.topic == 'greeting':
            return 'greeting_opening'
        if coerced.topic == 'psychological-portrait':
            return 'request_psychological_portrait'
        if coerced.topic == 'self-diagnosis':
            return 'self_diagnosis_soft'
        if coerced.topic == 'conversation-feedback':
            return 'request_conversation_feedback'
        return 'open_topic'
    if transition_kind == 'reframe_general' and fallback in {
        'confirm_scope',
        'abstractify_previous_question',
        'request_generalization',
    }:
        return fallback
    return _ACT_BY_TRANSITION.get(transition_kind, fallback or 'open_topic')


def coerce_frame(data: dict | None) -> DialogueFrame:
    payload = dict(data or {})
    return DialogueFrame(
        version=int(payload.get('version', 1) or 1),
        topic=payload.get('topic', '') or '',
        route=payload.get('route', '') or '',
        frame_type=payload.get('frame_type', '') or '',
        stance=payload.get('stance', 'personal') or 'personal',
        goal=payload.get('goal', 'opening') or 'opening',
        axis=payload.get('axis', '') or '',
        detail=payload.get('detail', '') or '',
        pending_slot=payload.get('pending_slot', '') or '',
        relation_to_previous=payload.get('relation_to_previous', 'new') or 'new',
        transition_kind=payload.get('transition_kind', '') or '',
        confidence=payload.get('confidence', '') or '',
        update_source=payload.get('update_source', '') or '',
    )


def frame_from_state(state: dict | None, *, dialogue_act: str = '') -> DialogueFrame:
    if isinstance(state, DialogueState):
        payload = state.as_dict()
    else:
        payload = dict(state or {})
    stance = payload.get('abstraction_level', 'personal') or 'personal'
    topic = payload.get('active_topic', '') or ''
    route = payload.get('active_route', '') or ''
    return DialogueFrame(
        topic=topic,
        route=route,
        frame_type=infer_frame_type(topic, stance),
        stance=stance,
        goal=goal_from_mode(payload.get('dialogue_mode', 'topic_opening') or 'topic_opening'),
        axis=payload.get('active_axis', '') or '',
        detail=payload.get('active_detail', '') or '',
        pending_slot=payload.get('pending_slot', '') or '',
        relation_to_previous=relation_from_act(dialogue_act),
        transition_kind='',
        confidence=payload.get('topic_confidence', '') or '',
        update_source=payload.get('update_source', '') or '',
    )


def build_frame_metadata(frame: dict | DialogueFrame | None) -> dict:
    coerced = frame if isinstance(frame, DialogueFrame) else coerce_frame(frame)
    return {
        'frame_topic': coerced.topic,
        'frame_route': coerced.route,
        'frame_type': coerced.frame_type,
        'frame_stance': coerced.stance,
        'frame_goal': coerced.goal,
        'frame_axis': coerced.axis,
        'frame_detail': coerced.detail,
        'frame_pending_slot': coerced.pending_slot,
        'frame_relation_to_previous': coerced.relation_to_previous,
        'frame_transition_kind': coerced.transition_kind,
        'frame_confidence': coerced.confidence,
        'frame_update_source': coerced.update_source,
    }
