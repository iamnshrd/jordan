"""Dialogue-state transitions for short-horizon conversational continuity."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

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


def _normalize(text: str) -> str:
    return ' '.join((text or '').lower().split())


def _contains_any(text: str, markers: list[str]) -> bool:
    return any(marker in text for marker in markers)


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
        if clarify_profile == 'psychological-portrait-request':
            return 'psychological-portrait'
        if clarify_profile == 'self-diagnosis-soft':
            return 'self-diagnosis'
        if clarify_profile == 'scope-topics':
            return 'scope-topics'
    if route_name == 'relationship-maintenance':
        if _contains_any(q, _RELATIONSHIP_LOSS_MARKERS):
            return 'relationship-loss-of-feeling'
        return 'relationship-knot'
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

    if dialogue_act in ('abstractify_previous_question', 'confirm_scope') and state.active_topic:
        next_state.dialogue_mode = 'followup_reframe'
        next_state.abstraction_level = 'general'
        next_state.pending_slot = 'pattern_family'
        next_state.turn_count_in_topic = max(1, state.turn_count_in_topic) + 1
    elif dialogue_act == 'personalize_previous_question' and state.active_topic:
        next_state.dialogue_mode = 'human_problem_clarify'
        next_state.abstraction_level = 'personal'
        next_state.pending_slot = 'narrowing_axis'
        next_state.turn_count_in_topic = max(1, state.turn_count_in_topic) + 1
        next_state.active_axis = ''
        next_state.active_detail = ''
    elif dialogue_act == 'supply_narrowing_axis' and state.active_topic:
        next_state.dialogue_mode = 'followup_narrowing'
        next_state.abstraction_level = state.abstraction_level or 'personal'
        next_state.pending_slot = 'concrete_manifestation'
        next_state.turn_count_in_topic = max(1, state.turn_count_in_topic) + 1
        next_state.active_axis = selected_axis or state.active_axis
        next_state.active_detail = ''
    elif dialogue_act == 'supply_concrete_manifestation' and state.active_topic:
        next_state.dialogue_mode = 'followup_deepen'
        next_state.abstraction_level = state.abstraction_level or 'personal'
        next_state.pending_slot = 'analysis_focus'
        next_state.turn_count_in_topic = max(1, state.turn_count_in_topic) + 1
        next_state.active_axis = state.active_axis
        next_state.active_detail = selected_detail or state.active_detail
    elif dialogue_act == 'request_mini_analysis' and state.active_topic:
        next_state.dialogue_mode = 'mini_analysis'
        next_state.abstraction_level = state.abstraction_level or 'personal'
        next_state.pending_slot = 'next_step'
        next_state.turn_count_in_topic = max(1, state.turn_count_in_topic) + 1
        next_state.active_axis = state.active_axis
        next_state.active_detail = state.active_detail
    elif dialogue_act == 'request_next_step' and state.active_topic:
        next_state.dialogue_mode = 'practical_next_step'
        next_state.abstraction_level = state.abstraction_level or 'personal'
        next_state.pending_slot = 'example_or_shift'
        next_state.turn_count_in_topic = max(1, state.turn_count_in_topic) + 1
        next_state.active_axis = state.active_axis
        next_state.active_detail = state.active_detail
    elif dialogue_act == 'request_example' and state.active_topic:
        next_state.dialogue_mode = 'example_illustration'
        next_state.abstraction_level = state.abstraction_level or 'personal'
        next_state.pending_slot = ''
        next_state.turn_count_in_topic = max(1, state.turn_count_in_topic) + 1
        next_state.active_axis = state.active_axis
        next_state.active_detail = state.active_detail
    elif dialogue_act == 'request_cause_list' and state.active_topic:
        next_state.dialogue_mode = 'cause_list'
        next_state.abstraction_level = state.abstraction_level or 'personal'
        next_state.pending_slot = 'narrowing_axis'
        next_state.turn_count_in_topic = max(1, state.turn_count_in_topic) + 1
        next_state.active_axis = ''
        next_state.active_detail = ''
    elif dialogue_act == 'reject_scope' and state.active_topic:
        next_state.dialogue_mode = 'human_problem_clarify'
        next_state.abstraction_level = 'personal'
        next_state.pending_slot = 'narrowing_axis'
        next_state.turn_count_in_topic = max(1, state.turn_count_in_topic) + 1
        next_state.active_axis = ''
        next_state.active_detail = ''
    else:
        active_topic = infer_active_topic(
            question,
            route_name=route_name or state.active_route,
            clarify_profile=clarify_profile,
        )
        if active_topic:
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
            elif dialogue_act == 'request_psychological_portrait' or clarify_profile == 'psychological-portrait-request':
                next_state.dialogue_mode = 'human_problem_clarify'
                next_state.pending_slot = 'pattern_selection'
            elif dialogue_act == 'self_diagnosis_soft' or clarify_profile == 'self-diagnosis-soft':
                next_state.dialogue_mode = 'human_problem_clarify'
                next_state.pending_slot = 'symptom_narrowing'
            elif decision_type == 'clarify' and clarify_profile:
                next_state.dialogue_mode = 'human_problem_clarify'
                next_state.pending_slot = 'narrowing_axis'
            elif decision_type == 'respond_kb':
                next_state.dialogue_mode = 'kb_answer'
                next_state.pending_slot = ''
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
    if next_state.active_topic == 'relationship-loss-of-feeling':
        next_state.candidate_axes = [
            'resentment',
            'coldness',
            'loss_of_desire',
            'loss_of_respect',
            'unspoken_conflict',
        ]
    elif next_state.active_topic == 'psychological-portrait':
        next_state.candidate_axes = [
            'discipline',
            'closeness',
            'resentment',
            'avoidance',
            'self_deception',
        ]
    elif next_state.active_topic == 'self-diagnosis':
        next_state.candidate_axes = [
            'emotional_flatness',
            'loss_of_interest',
            'exhaustion',
            'social_disconnection',
            'loss_of_aim',
        ]
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
