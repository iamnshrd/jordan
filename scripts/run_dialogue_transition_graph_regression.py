#!/usr/bin/env python3
from __future__ import annotations

from _helpers import emit_report
from library._core.runtime.dialogue_family_registry import get_dialogue_transition_hints
from library._core.runtime.dialogue_family_registry import is_dialogue_transition_allowed
from library._core.runtime.dialogue_state import advance_dialogue_state


def main() -> None:
    greeting_state = {
        'active_topic': 'greeting',
        'active_route': 'general',
        'dialogue_mode': 'topic_opening',
        'abstraction_level': 'general',
        'pending_slot': '',
        'turn_count_in_topic': 1,
    }
    menu_state = {
        'active_topic': 'scope-topics',
        'active_route': 'general',
        'dialogue_mode': 'scope_clarify',
        'abstraction_level': 'general',
        'pending_slot': 'topic_selection',
        'turn_count_in_topic': 1,
    }

    greeting_after_cause = advance_dialogue_state(
        greeting_state,
        question='какие основные причины?',
        dialogue_act='request_cause_list',
    )
    menu_after_detail = advance_dialogue_state(
        menu_state,
        question='скорее пустота',
        dialogue_act='supply_concrete_manifestation',
        selected_detail='numbness',
    )
    loneliness_axis = get_dialogue_transition_hints('loneliness-rejection', 'axis_answer')
    loneliness_detail = get_dialogue_transition_hints('loneliness-rejection', 'detail_answer')
    loneliness_mini = get_dialogue_transition_hints('loneliness-rejection', 'mini_analysis')
    loneliness_next = get_dialogue_transition_hints('loneliness-rejection', 'next_step')
    loneliness_example = get_dialogue_transition_hints('loneliness-rejection', 'example')

    results = [
        {
            'name': 'relationship_clarify_allows_axis_answer',
            'pass': is_dialogue_transition_allowed(
                'relationship-loss-of-feeling',
                'axis_answer',
                dialogue_mode='human_problem_clarify',
                pending_slot='narrowing_axis',
                abstraction_level='personal',
            ),
        },
        {
            'name': 'relationship_opening_blocks_detail_answer',
            'pass': not is_dialogue_transition_allowed(
                'relationship-loss-of-feeling',
                'detail_answer',
                dialogue_mode='human_problem_clarify',
                pending_slot='narrowing_axis',
                abstraction_level='personal',
            ),
        },
        {
            'name': 'scope_menu_blocks_detail_answer',
            'pass': not is_dialogue_transition_allowed(
                'scope-topics',
                'detail_answer',
                dialogue_mode='scope_clarify',
                pending_slot='topic_selection',
                abstraction_level='general',
            ),
        },
        {
            'name': 'greeting_blocks_cause_list',
            'pass': not is_dialogue_transition_allowed(
                'greeting',
                'cause_list',
                dialogue_mode='topic_opening',
                pending_slot='',
                abstraction_level='general',
            ),
        },
        {
            'name': 'foundations_allows_cause_list_and_next_step_path',
            'pass': (
                is_dialogue_transition_allowed(
                    'relationship-foundations',
                    'cause_list',
                    dialogue_mode='human_problem_clarify',
                    pending_slot='pattern_family',
                    abstraction_level='general',
                )
                and is_dialogue_transition_allowed(
                    'relationship-foundations',
                    'next_step',
                    dialogue_mode='cause_list',
                    pending_slot='narrowing_axis',
                    abstraction_level='general',
                )
            ),
        },
        {
            'name': 'foundations_blocks_detail_without_axis_path',
            'pass': not is_dialogue_transition_allowed(
                'relationship-foundations',
                'detail_answer',
                dialogue_mode='followup_reframe',
                pending_slot='pattern_family',
                abstraction_level='general',
            ),
        },
        {
            'name': 'covered_family_exposes_full_progression_graph',
            'pass': (
                loneliness_axis.get('dialogue_mode') == 'followup_narrowing'
                and loneliness_detail.get('dialogue_mode') == 'followup_deepen'
                and loneliness_mini.get('dialogue_mode') == 'mini_analysis'
                and loneliness_next.get('dialogue_mode') == 'practical_next_step'
                and loneliness_example.get('dialogue_mode') == 'example_illustration'
            ),
        },
        {
            'name': 'state_machine_rejects_invalid_greeting_progression',
            'pass': (
                greeting_after_cause.dialogue_mode == 'topic_opening'
                and greeting_after_cause.active_topic == 'greeting'
                and greeting_after_cause.pending_slot == ''
            ),
        },
        {
            'name': 'state_machine_rejects_invalid_menu_detail_progression',
            'pass': (
                menu_after_detail.dialogue_mode == 'scope_clarify'
                and menu_after_detail.active_topic == 'scope-topics'
                and menu_after_detail.pending_slot == 'topic_selection'
            ),
        },
    ]

    emit_report(
        results,
        samples={
            'greeting_after_cause': greeting_after_cause.as_dict(),
            'menu_after_detail': menu_after_detail.as_dict(),
            'loneliness_axis': loneliness_axis,
            'loneliness_detail': loneliness_detail,
            'loneliness_mini': loneliness_mini,
            'loneliness_next': loneliness_next,
            'loneliness_example': loneliness_example,
        },
    )


if __name__ == '__main__':
    main()
