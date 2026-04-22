#!/usr/bin/env python3
from __future__ import annotations

from _helpers import emit_report
from library._core.runtime.dialogue_family_registry import DIALOGUE_FAMILY_REGISTRY
from library._core.runtime.dialogue_family_registry import get_dialogue_acknowledgement_hint
from library._core.runtime.dialogue_family_registry import get_dialogue_family_spec
from library._core.runtime.dialogue_family_registry import get_dialogue_render_hints
from library._core.runtime.dialogue_family_registry import get_dialogue_transition_hints
from library._core.runtime.dialogue_family_registry import infer_dialogue_family
from library._core.runtime.dialogue_family_registry import resolve_dialogue_transition


def main() -> None:
    relationship = infer_dialogue_family('Из чего строится по-настоящему крепкий брак?')
    meaning = infer_dialogue_family('Я вообще не понимаю, ради чего двигаться дальше по жизни')
    self_eval = infer_dialogue_family('Почему я сам себе всё ломаю?')
    shame = infer_dialogue_family('Мне омерзительно смотреть на себя')
    menu = infer_dialogue_family('Что мы можем обсудить с тобой?')
    feedback = infer_dialogue_family('ты задаёшь слишком много вопросов')
    greeting = infer_dialogue_family('Добрый вечер, доктор Питерсон')
    resentment = infer_dialogue_family('Я коплю обиду и не могу её отпустить')
    self_deception = infer_dialogue_family('Я всё время вру себе о своих мотивах')
    fear = infer_dialogue_family('Я боюсь сделать шаг и потерять одобрение')
    loneliness = infer_dialogue_family('Меня не выбирают и я чувствую себя совсем один')
    parenting = infer_dialogue_family('Мой ребёнок не слушается и я слишком мягкая')
    tragedy = infer_dialogue_family('Я не могу пережить утрату и начинаю озлобляться')
    self_eval_spec = get_dialogue_family_spec('self-evaluation')
    shame_spec = get_dialogue_family_spec('shame-self-contempt')
    greeting_spec = get_dialogue_family_spec('greeting')
    self_eval_axis_transition = get_dialogue_transition_hints('self-evaluation', 'axis_answer')
    shame_next_step_transition = get_dialogue_transition_hints('shame-self-contempt', 'next_step')
    relationship_reframe_general = get_dialogue_transition_hints('relationship-loss-of-feeling', 'reframe_general')
    relationship_reframe_personal = get_dialogue_transition_hints('relationship-loss-of-feeling', 'reframe_personal')
    greeting_opening_transition = get_dialogue_transition_hints('greeting', 'opening')
    loneliness_axis_transition = resolve_dialogue_transition(
        'loneliness-rejection',
        'axis_answer',
        goal='clarify',
        dialogue_mode='human_problem_clarify',
        pending_slot='narrowing_axis',
        abstraction_level='personal',
    )
    loneliness_detail_transition = resolve_dialogue_transition(
        'loneliness-rejection',
        'detail_answer',
        goal='clarify',
        dialogue_mode='followup_narrowing',
        pending_slot='concrete_manifestation',
        abstraction_level='personal',
    )
    relationship_overview_render = get_dialogue_render_hints('relationship-loss-of-feeling', 'overview')
    self_eval_clarify_render = get_dialogue_render_hints('self-evaluation', 'clarify')
    menu_render = get_dialogue_render_hints('scope-topics', 'menu')
    greeting_render = get_dialogue_render_hints('greeting', 'opening')
    shame_next_step_render = get_dialogue_render_hints('shame-self-contempt', 'next_step')
    portrait_example_render = get_dialogue_render_hints('psychological-portrait', 'example')
    relationship_reframe_ack = get_dialogue_acknowledgement_hint(
        topic='relationship-loss-of-feeling',
        relation='reframe',
        goal='overview',
        stance='general',
    )
    diagnosis_personal_ack = get_dialogue_acknowledgement_hint(
        topic='self-diagnosis',
        relation='reframe',
        goal='clarify',
        stance='personal',
    )

    topics = {spec.topic for spec in DIALOGUE_FAMILY_REGISTRY}

    results = [
        {
            'name': 'registry_contains_expected_core_families',
            'pass': {
                'relationship-foundations',
                'lost-and-aimless',
                'scope-topics',
                'conversation-feedback',
                'self-evaluation',
                'shame-self-contempt',
                'greeting',
            }.issubset(topics),
        },
        {
            'name': 'registry_maps_relationship_paraphrase',
            'pass': (
                relationship.get('topic_candidate') == 'relationship-foundations'
                and relationship.get('goal_candidate') == 'overview'
            ),
        },
        {
            'name': 'registry_maps_meaning_paraphrase',
            'pass': (
                meaning.get('topic_candidate') == 'lost-and-aimless'
                and meaning.get('goal_candidate') == 'clarify'
            ),
        },
        {
            'name': 'registry_maps_self_evaluation_and_shame',
            'pass': (
                self_eval.get('topic_candidate') == 'self-evaluation'
                and shame.get('topic_candidate') == 'shame-self-contempt'
                and menu.get('topic_candidate') == 'scope-topics'
                and feedback.get('topic_candidate') == 'conversation-feedback'
                and greeting.get('topic_candidate') == 'greeting'
            ),
        },
        {
            'name': 'registry_maps_new_human_problem_families',
            'pass': (
                resentment.get('topic_candidate') == 'resentment-conflict'
                and self_deception.get('topic_candidate') == 'self-deception'
                and fear.get('topic_candidate') == 'fear-and-price'
                and loneliness.get('topic_candidate') == 'loneliness-rejection'
                and parenting.get('topic_candidate') == 'parenting-boundaries'
                and tragedy.get('topic_candidate') == 'tragedy-bitterness'
            ),
        },
        {
            'name': 'registry_exposes_opening_transition_hints',
            'pass': (
                self_eval_spec is not None
                and self_eval_spec.opening_mode == 'human_problem_clarify'
                and self_eval_spec.opening_pending_slot == 'pattern_selection'
                and 'self_deception' in self_eval_spec.candidate_axes
                and shame_spec is not None
                and shame_spec.opening_pending_slot == 'narrowing_axis'
                and 'humiliation' in shame_spec.candidate_axes
                and greeting_spec is not None
                and greeting_spec.opening_mode == 'topic_opening'
                and greeting_spec.opening_pending_slot == ''
            ),
        },
        {
            'name': 'registry_exposes_greeting_opening_contract',
            'pass': (
                greeting_opening_transition.get('dialogue_mode') == 'topic_opening'
                and greeting_opening_transition.get('pending_slot') == ''
                and greeting_render.get('profile') == 'greeting-opening'
                and greeting_render.get('reason_code') == 'greeting-opening'
            ),
        },
        {
            'name': 'registry_exposes_followup_transition_hints',
            'pass': (
                self_eval_axis_transition.get('dialogue_mode') == 'followup_narrowing'
                and self_eval_axis_transition.get('pending_slot') == 'concrete_manifestation'
                and shame_next_step_transition.get('dialogue_mode') == 'practical_next_step'
                and shame_next_step_transition.get('pending_slot') == 'example_or_shift'
            ),
        },
        {
            'name': 'registry_exposes_declarative_transition_graph',
            'pass': (
                loneliness_axis_transition.get('goal') == 'clarify'
                and loneliness_axis_transition.get('dialogue_mode') == 'followup_narrowing'
                and loneliness_axis_transition.get('pending_slot') == 'concrete_manifestation'
                and loneliness_detail_transition.get('goal') == 'clarify'
                and loneliness_detail_transition.get('dialogue_mode') == 'followup_deepen'
                and loneliness_detail_transition.get('pending_slot') == 'analysis_focus'
            ),
        },
        {
            'name': 'registry_exposes_reframe_transition_hints',
            'pass': (
                relationship_reframe_general.get('dialogue_mode') == 'followup_reframe'
                and relationship_reframe_general.get('pending_slot') == 'pattern_family'
                and relationship_reframe_personal.get('dialogue_mode') == 'human_problem_clarify'
                and relationship_reframe_personal.get('pending_slot') == 'narrowing_axis'
            ),
        },
        {
            'name': 'registry_exposes_render_hints',
            'pass': (
                relationship_overview_render.get('profile') == 'abstractify-relationship-loss-of-feeling'
                and relationship_overview_render.get('reason_code') == 'abstractify-relationship-loss-of-feeling'
                and self_eval_clarify_render.get('profile') == 'self-evaluation-request'
                and self_eval_clarify_render.get('question_kind') == 'pattern_selection'
                and menu_render.get('profile') == 'scope-topics'
                and menu_render.get('clarify_type') == 'scope'
            ),
        },
        {
            'name': 'registry_exposes_progression_render_hints',
            'pass': (
                shame_next_step_render.get('render_kind') == 'next_step'
                and shame_next_step_render.get('reason_code') == 'shame-self-contempt-next-step'
                and portrait_example_render.get('render_kind') == 'example'
                and portrait_example_render.get('question_kind') == 'illustrative_example'
            ),
        },
        {
            'name': 'registry_exposes_acknowledgement_hints',
            'pass': (
                'не о твоём частном случае' in relationship_reframe_ack.lower()
                and 'к твоему личному опыту' in diagnosis_personal_ack.lower()
            ),
        },
    ]

    emit_report(
        results,
        samples={
            'registry_topics': sorted(topics),
            'relationship': relationship,
            'meaning': meaning,
            'self_evaluation': self_eval,
            'shame': shame,
            'menu': menu,
            'feedback': feedback,
            'greeting': greeting,
            'resentment': resentment,
            'self_deception': self_deception,
            'fear': fear,
            'loneliness': loneliness,
            'parenting': parenting,
            'tragedy': tragedy,
            'self_evaluation_spec': {
                'opening_mode': self_eval_spec.opening_mode if self_eval_spec else '',
                'opening_pending_slot': self_eval_spec.opening_pending_slot if self_eval_spec else '',
                'candidate_axes': list(self_eval_spec.candidate_axes) if self_eval_spec else [],
            },
            'shame_spec': {
                'opening_mode': shame_spec.opening_mode if shame_spec else '',
                'opening_pending_slot': shame_spec.opening_pending_slot if shame_spec else '',
                'candidate_axes': list(shame_spec.candidate_axes) if shame_spec else [],
            },
            'self_evaluation_axis_transition': self_eval_axis_transition,
            'shame_next_step_transition': shame_next_step_transition,
            'relationship_reframe_general': relationship_reframe_general,
            'relationship_reframe_personal': relationship_reframe_personal,
            'greeting_opening_transition': greeting_opening_transition,
            'loneliness_axis_transition': loneliness_axis_transition,
            'loneliness_detail_transition': loneliness_detail_transition,
            'relationship_overview_render': relationship_overview_render,
            'self_evaluation_clarify_render': self_eval_clarify_render,
            'menu_render': menu_render,
            'greeting_render': greeting_render,
            'shame_next_step_render': shame_next_step_render,
            'portrait_example_render': portrait_example_render,
            'relationship_reframe_ack': relationship_reframe_ack,
            'diagnosis_personal_ack': diagnosis_personal_ack,
        },
    )


if __name__ == '__main__':
    main()
