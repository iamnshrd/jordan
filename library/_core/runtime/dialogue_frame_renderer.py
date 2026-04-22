"""Frame-first clarification planning for dialogue-driven rendering."""
from __future__ import annotations

from dataclasses import dataclass

from library._core.runtime.dialogue_family_registry import get_dialogue_render_hints


@dataclass(frozen=True)
class FrameRenderPlan:
    render_kind: str
    clarify_type: str
    route_name: str
    profile: str
    template_id: str
    question_kind: str
    reason_code: str
    response_mode: str = 'frame'
    topic: str = ''
    stance: str = 'personal'
    axis: str = ''
    detail: str = ''
    source_act: str = ''


_PORTRAIT_REQUEST_MARKERS = (
    'психологический портрет',
    'мой портрет',
    'разбери мой характер',
)

_SELF_DIAGNOSIS_REQUEST_MARKERS = (
    'у меня ангедония',
    'подозреваю, что у меня',
    'кажется, что у меня',
    'похоже, что у меня',
)


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def plan_frame_render(*,
                      route_name: str,
                      dialogue_state: dict | None = None,
                      dialogue_frame: dict | None = None,
                      dialogue_act: str = '',
                      selected_axis: str = '',
                      selected_detail: str = '') -> FrameRenderPlan | None:
    state = dialogue_state or {}
    frame = dialogue_frame or {}

    frame_topic = frame.get('topic') or state.get('active_topic', '')
    frame_goal = frame.get('goal', '')
    frame_stance = frame.get('stance') or state.get('abstraction_level', 'personal')
    frame_relation = frame.get('relation_to_previous', '')
    frame_transition = frame.get('transition_kind', '')
    active_route = state.get('active_route') or route_name
    active_axis = selected_axis or state.get('active_axis', '')
    active_detail = selected_detail or state.get('active_detail', '')

    if (
        frame_relation == 'answer_slot'
        and frame_goal == 'clarify'
        and frame_topic
        and selected_axis
        and frame_transition in {'axis_answer', ''}
    ):
        return FrameRenderPlan(
            render_kind='axis_followup',
            clarify_type='human_problem',
            route_name=active_route,
            profile='axis-followup',
            template_id=f'axis-followup.{frame_topic}.v1',
            question_kind='concrete_manifestation',
            reason_code=f'{frame_topic}-axis-followup',
            topic=frame_topic,
            stance=frame_stance,
            axis=selected_axis,
            source_act=dialogue_act,
        )

    if (
        frame_relation == 'answer_slot'
        and frame_goal == 'clarify'
        and frame_topic
        and selected_detail
        and frame_transition in {'detail_answer', ''}
    ):
        return FrameRenderPlan(
            render_kind='detail_followup',
            clarify_type='human_problem',
            route_name=active_route,
            profile='detail-followup',
            template_id=f'detail-followup.{frame_topic}.v1',
            question_kind='analysis_focus',
            reason_code=f'{frame_topic}-detail-followup',
            topic=frame_topic,
            stance=frame_stance,
            axis=state.get('active_axis', ''),
            detail=selected_detail,
            source_act=dialogue_act,
        )

    render_hints = get_dialogue_render_hints(frame_topic, frame_goal) if frame_topic else {}

    if render_hints and frame_relation != 'answer_slot':
        response_mode = 'act' if dialogue_act == 'reject_scope' else render_hints.get('response_mode', 'frame')
        return FrameRenderPlan(
            render_kind=render_hints.get('render_kind', 'profile'),
            clarify_type=render_hints.get('clarify_type', 'human_problem'),
            route_name=active_route,
            profile=render_hints.get('profile', ''),
            template_id=render_hints.get('template_id', ''),
            question_kind=render_hints.get('question_kind', ''),
            reason_code=render_hints.get('reason_code', ''),
            response_mode=response_mode,
            topic=frame_topic,
            stance=frame_stance,
            axis=active_axis,
            detail=active_detail,
            source_act=dialogue_act,
        )

    return None


def plan_act_fallback_render(*,
                             question: str,
                             route_name: str,
                             dialogue_state: dict | None = None,
                             dialogue_act: str = '',
                             selected_axis: str = '',
                             selected_detail: str = '') -> FrameRenderPlan | None:
    state = dialogue_state or {}
    active_topic = state.get('active_topic', '')
    active_route = state.get('active_route') or route_name
    abstraction_level = state.get('abstraction_level', 'personal') or 'personal'
    active_axis = selected_axis or state.get('active_axis', '')
    active_detail = selected_detail or state.get('active_detail', '')
    q = ' '.join((question or '').lower().split())

    profile_by_topic = {
        'relationship-loss-of-feeling': 'relationship-knot',
        'psychological-portrait': 'psychological-portrait-request',
        'self-diagnosis': 'self-diagnosis-soft',
    }
    clarify_type_by_profile = {
        'scope-topics': 'scope',
        'greeting-opening': 'scope',
    }
    question_kind_by_profile = {
        'abstractify-relationship-loss-of-feeling': 'topic_variant',
        'relationship-knot': 'narrowing',
        'psychological-portrait-request': 'pattern_selection',
        'self-diagnosis-soft': 'symptom_narrowing',
        'scope-topics': 'topic_selection',
        'greeting-opening': 'topic_selection',
    }

    if dialogue_act in {'abstractify_previous_question', 'confirm_scope'} and active_topic == 'relationship-loss-of-feeling':
        return FrameRenderPlan(
            render_kind='profile',
            clarify_type='scope',
            route_name=active_route,
            profile='abstractify-relationship-loss-of-feeling',
            template_id='abstractify-relationship-loss-of-feeling.v1',
            question_kind='topic_variant',
            reason_code='abstractify-relationship-loss-of-feeling',
            response_mode='act',
            topic=active_topic,
            stance=abstraction_level,
            source_act=dialogue_act,
        )
    if dialogue_act in {'personalize_previous_question', 'reject_scope'} and active_topic in profile_by_topic:
        profile = profile_by_topic[active_topic]
        return FrameRenderPlan(
            render_kind='profile',
            clarify_type='human_problem',
            route_name=active_route,
            profile=profile,
            template_id=f'{profile}.v1',
            question_kind=question_kind_by_profile.get(profile, 'narrowing'),
            reason_code=profile if profile != 'relationship-knot' else 'relationship-knot',
            response_mode='act',
            topic=active_topic,
            stance=abstraction_level,
            source_act=dialogue_act,
        )
    if dialogue_act == 'supply_narrowing_axis' and active_topic:
        return FrameRenderPlan(
            render_kind='axis_followup',
            clarify_type='human_problem',
            route_name=active_route,
            profile='axis-followup',
            template_id=f'axis-followup.{active_topic}.v1',
            question_kind='concrete_manifestation',
            reason_code=f'{active_topic}-axis-followup',
            response_mode='act',
            topic=active_topic,
            stance=abstraction_level,
            axis=active_axis,
            source_act=dialogue_act,
        )
    if dialogue_act == 'supply_concrete_manifestation' and active_topic:
        return FrameRenderPlan(
            render_kind='detail_followup',
            clarify_type='human_problem',
            route_name=active_route,
            profile='detail-followup',
            template_id=f'detail-followup.{active_topic}.v1',
            question_kind='analysis_focus',
            reason_code=f'{active_topic}-detail-followup',
            response_mode='act',
            topic=active_topic,
            stance=abstraction_level,
            axis=state.get('active_axis', ''),
            detail=selected_detail,
            source_act=dialogue_act,
        )
    progression = {
        'request_mini_analysis': ('mini_analysis', 'mini-analysis', 'meaning_reframe', f'{active_topic}-mini-analysis'),
        'request_next_step': ('next_step', 'next-step', 'practical_next_step', f'{active_topic}-next-step'),
        'request_example': ('example', 'example', 'illustrative_example', f'{active_topic}-example'),
        'request_cause_list': ('cause_list', 'cause-list', 'cause_list', f'{active_topic}-cause-list'),
    }.get(dialogue_act)
    if progression and active_topic:
        render_kind, profile, question_kind, reason_code = progression
        return FrameRenderPlan(
            render_kind=render_kind,
            clarify_type='human_problem',
            route_name=active_route,
            profile=profile,
            template_id=f'{profile}.{active_topic}.v1',
            question_kind=question_kind,
            reason_code=reason_code,
            response_mode='act',
            topic=active_topic,
            stance=abstraction_level,
            axis=state.get('active_axis', ''),
            detail=state.get('active_detail', ''),
            source_act=dialogue_act,
        )
    if dialogue_act == 'request_menu':
        return FrameRenderPlan(
            render_kind='profile',
            clarify_type='scope',
            route_name=route_name,
            profile='scope-topics',
            template_id='scope-topics.v1',
            question_kind='topic_selection',
            reason_code='scope-topics',
            response_mode='act',
            topic='scope-topics',
            stance='general',
            source_act=dialogue_act,
        )
    if dialogue_act == 'greeting_opening':
        return FrameRenderPlan(
            render_kind='profile',
            clarify_type='scope',
            route_name='general',
            profile='greeting-opening',
            template_id='greeting-opening.v1',
            question_kind='topic_selection',
            reason_code='greeting-opening',
            response_mode='act',
            topic='greeting',
            stance='general',
            source_act=dialogue_act,
        )
    if dialogue_act in {'topic_shift', 'request_psychological_portrait'} and _contains_any(q, _PORTRAIT_REQUEST_MARKERS):
        return FrameRenderPlan(
            render_kind='profile',
            clarify_type='human_problem',
            route_name='general',
            profile='psychological-portrait-request',
            template_id='psychological-portrait-request.v1',
            question_kind='pattern_selection',
            reason_code='psychological-portrait-request',
            response_mode='act',
            topic='psychological-portrait',
            stance='personal',
            source_act=dialogue_act,
        )
    if dialogue_act in {'topic_shift', 'self_diagnosis_soft'} and _contains_any(q, _SELF_DIAGNOSIS_REQUEST_MARKERS):
        return FrameRenderPlan(
            render_kind='profile',
            clarify_type='human_problem',
            route_name='general',
            profile='self-diagnosis-soft',
            template_id='self-diagnosis-soft.v1',
            question_kind='symptom_narrowing',
            reason_code='self-diagnosis-soft',
            response_mode='act',
            topic='self-diagnosis',
            stance='personal',
            source_act=dialogue_act,
        )
    return None
