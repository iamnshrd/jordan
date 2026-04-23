#!/usr/bin/env python3
from __future__ import annotations

from _helpers import emit_report, temp_store
from library._core.runtime import planner
from library._core.runtime.dialogue_family_registry import build_dialogue_family_candidates
from library._core.runtime.dialogue_frame import DialogueFrame
from library._core.runtime.dialogue_update import infer_dialogue_update
from library._core.runtime.llm_classifiers import (
    reset_control_command_classifier,
    reset_family_classifier,
    reset_marginal_router,
    set_control_command_classifier,
    set_family_classifier,
    set_marginal_router,
)


def _build_control_command_classifier():
    def control_command(*, request):
        question = (request.question or '').strip().lower()
        mapping = {
            'я не понимаю о чём ты': {
                'command_name': 'repair_misunderstanding',
                'confidence': 0.95,
                'reason': 'repair_signal',
                'kb_posture': 'skip_kb',
            },
            'так разговора у нас не получится': {
                'command_name': 'repair_meta_friction',
                'confidence': 0.96,
                'reason': 'friction_signal',
                'kb_posture': 'skip_kb',
            },
            'объясни проще': {
                'command_name': 'repair_wrong_level',
                'confidence': 0.94,
                'reason': 'too_abstract',
                'kb_posture': 'skip_kb',
            },
            'предложи что делать': {
                'command_name': 'start_broad_help_opening',
                'confidence': 0.94,
                'reason': 'vague_help',
                'kb_posture': 'skip_kb',
            },
            'я подозреваю, что у меня ангедония': {
                'command_name': 'start_symptom_self_report_opening',
                'confidence': 0.93,
                'reason': 'symptom_signal',
                'kb_posture': 'skip_kb',
            },
            'я имею в виду абстрактно': {
                'command_name': 'shift_scope_more_general',
                'confidence': 0.92,
                'reason': 'scope_shift',
                'abstraction_shift': 'more_general',
                'kb_posture': 'skip_kb',
            },
            'давай обсудим отношения': {
                'command_name': 'start_relationship_broad_opening',
                'confidence': 0.95,
                'reason': 'broad_relationship_opening',
                'kb_posture': 'skip_kb',
            },
            'угадай, что я хочу спросить': {
                'command_name': 'start_social_opening',
                'confidence': 0.91,
                'reason': 'teasing_opening',
                'kb_posture': 'skip_kb',
            },
        }
        return mapping.get(question, {'command_name': 'no_command', 'confidence': 0.90, 'reason': 'none'})

    return control_command


def _build_no_special_router():
    def marginal_router(*, request):
        return {
            'special_route': 'no_special_route',
            'confidence': 0.99,
            'reason': 'disabled_for_family_regression',
        }

    return marginal_router


def main() -> None:
    shortlist = build_dialogue_family_candidates('Проверяем рендерер')

    def override_family(*, request):
        return {
            'topic_candidate': 'appearance-self-presentation',
            'route_candidate': 'general',
            'stance_shift': 'personal',
            'goal_candidate': 'clarify',
            'confidence': 0.96,
            'reason': 'appearance_override',
        }

    set_marginal_router(_build_no_special_router())
    set_family_classifier(override_family)
    override_update = infer_dialogue_update(
        'Как стать красивее',
        dialogue_act='open_topic',
        dialogue_state={
            'active_topic': '',
            'active_route': '',
            'abstraction_level': 'personal',
            'pending_slot': '',
            'dialogue_mode': '',
        },
        dialogue_frame=DialogueFrame().as_dict(),
    )
    reset_family_classifier()
    reset_marginal_router()

    def low_conf_family(*, request):
        return {
            'topic_candidate': 'appearance-self-presentation',
            'route_candidate': 'general',
            'stance_shift': 'personal',
            'goal_candidate': 'clarify',
            'confidence': 0.42,
            'reason': 'uncertain_guess',
        }

    set_marginal_router(_build_no_special_router())
    set_family_classifier(low_conf_family)
    low_conf_update = infer_dialogue_update(
        'Как стать красивее',
        dialogue_act='open_topic',
        dialogue_state={},
        dialogue_frame=DialogueFrame().as_dict(),
    )
    reset_family_classifier()
    reset_marginal_router()

    def invalid_topic_family(*, request):
        return {
            'topic_candidate': 'invented-topic',
            'route_candidate': 'general',
            'stance_shift': 'personal',
            'goal_candidate': 'clarify',
            'confidence': 0.98,
            'reason': 'bad_output',
        }

    set_marginal_router(_build_no_special_router())
    set_family_classifier(invalid_topic_family)
    invalid_topic_update = infer_dialogue_update(
        'Как стать красивее',
        dialogue_act='open_topic',
        dialogue_state={},
        dialogue_frame=DialogueFrame().as_dict(),
    )
    reset_family_classifier()
    reset_marginal_router()

    slot_calls = {'count': 0}

    def slot_family(*, request):
        slot_calls['count'] += 1
        return {
            'topic_candidate': 'social-small-talk',
            'route_candidate': 'general',
            'stance_shift': 'general',
            'goal_candidate': 'opening',
            'confidence': 0.96,
            'reason': 'should_not_happen',
        }

    set_family_classifier(slot_family)
    slot_update = infer_dialogue_update(
        'скорее обида',
        dialogue_act='supply_narrowing_axis',
        dialogue_state={
            'active_topic': 'relationship-loss-of-feeling',
            'active_route': 'relationship-maintenance',
            'abstraction_level': 'personal',
            'pending_slot': 'narrowing_axis',
            'dialogue_mode': 'human_problem_clarify',
        },
        dialogue_frame={
            'topic': 'relationship-loss-of-feeling',
            'route': 'relationship-maintenance',
            'frame_type': 'relationship_problem',
            'stance': 'personal',
            'goal': 'clarify',
            'pending_slot': 'narrowing_axis',
            'relation_to_previous': 'continue',
            'transition_kind': 'opening',
        },
        selected_axis='resentment',
    )
    reset_family_classifier()

    policy_calls = {'count': 0}

    def policy_family(*, request):
        policy_calls['count'] += 1
        return {
            'topic_candidate': 'social-small-talk',
            'route_candidate': 'general',
            'stance_shift': 'general',
            'goal_candidate': 'opening',
            'confidence': 0.96,
            'reason': 'should_not_happen',
        }

    set_family_classifier(policy_family)
    policy_update = infer_dialogue_update(
        'Напиши код на python для телеграм-бота',
        dialogue_act='open_topic',
        dialogue_state={},
        dialogue_frame=DialogueFrame().as_dict(),
    )
    reset_family_classifier()

    control_command = _build_control_command_classifier()
    set_control_command_classifier(control_command)
    repair_update = infer_dialogue_update(
        'Я не понимаю о чём ты',
        dialogue_act='open_topic',
        dialogue_state={
            'active_topic': 'relationship-knot',
            'active_route': 'relationship-maintenance',
            'abstraction_level': 'personal',
            'pending_slot': 'narrowing_axis',
            'dialogue_mode': 'human_problem_clarify',
        },
        dialogue_frame={
            'topic': 'relationship-knot',
            'route': 'relationship-maintenance',
            'frame_type': 'relationship_problem',
            'stance': 'personal',
            'goal': 'clarify',
            'pending_slot': 'narrowing_axis',
            'relation_to_previous': 'continue',
            'transition_kind': 'opening',
        },
    )
    friction_update = infer_dialogue_update(
        'Так разговора у нас не получится',
        dialogue_act='open_topic',
        dialogue_state={'active_topic': 'general'},
        dialogue_frame=DialogueFrame().as_dict(),
    )
    level_update = infer_dialogue_update(
        'Объясни проще',
        dialogue_act='open_topic',
        dialogue_state={'active_topic': 'general'},
        dialogue_frame=DialogueFrame().as_dict(),
    )
    vague_update = infer_dialogue_update(
        'Предложи что делать',
        dialogue_act='open_topic',
        dialogue_state={'active_topic': 'general'},
        dialogue_frame=DialogueFrame().as_dict(),
    )
    symptom_update = infer_dialogue_update(
        'я подозреваю, что у меня ангедония',
        dialogue_act='open_topic',
        dialogue_state={'active_topic': 'general'},
        dialogue_frame=DialogueFrame().as_dict(),
    )
    scope_update = infer_dialogue_update(
        'Я имею в виду абстрактно',
        dialogue_act='open_topic',
        dialogue_state={
            'active_topic': 'relationship-knot',
            'active_route': 'relationship-maintenance',
            'abstraction_level': 'personal',
            'pending_slot': 'narrowing_axis',
            'dialogue_mode': 'human_problem_clarify',
        },
        dialogue_frame={
            'topic': 'relationship-knot',
            'route': 'relationship-maintenance',
            'frame_type': 'relationship_problem',
            'stance': 'personal',
            'goal': 'clarify',
            'pending_slot': 'narrowing_axis',
            'relation_to_previous': 'continue',
            'transition_kind': 'opening',
        },
    )
    relationship_update = infer_dialogue_update(
        'Давай обсудим отношения',
        dialogue_act='open_topic',
        dialogue_state={'active_topic': 'general'},
        dialogue_frame=DialogueFrame().as_dict(),
    )
    teasing_update = infer_dialogue_update(
        'угадай, что я хочу спросить',
        dialogue_act='open_topic',
        dialogue_state={'active_topic': 'general'},
        dialogue_frame=DialogueFrame().as_dict(),
    )
    reset_control_command_classifier()

    marginal_slot_calls = {'count': 0}

    def slot_marginal(*, request):
        marginal_slot_calls['count'] += 1
        return {
            'command_name': 'repair_misunderstanding',
            'confidence': 0.99,
            'reason': 'should_not_happen',
            'kb_posture': 'skip_kb',
        }

    set_control_command_classifier(slot_marginal)
    marginal_slot_update = infer_dialogue_update(
        'скорее обида',
        dialogue_act='supply_narrowing_axis',
        dialogue_state={
            'active_topic': 'relationship-loss-of-feeling',
            'active_route': 'relationship-maintenance',
            'abstraction_level': 'personal',
            'pending_slot': 'narrowing_axis',
            'dialogue_mode': 'human_problem_clarify',
        },
        dialogue_frame={
            'topic': 'relationship-loss-of-feeling',
            'route': 'relationship-maintenance',
            'frame_type': 'relationship_problem',
            'stance': 'personal',
            'goal': 'clarify',
            'pending_slot': 'narrowing_axis',
            'relation_to_previous': 'continue',
            'transition_kind': 'opening',
        },
        selected_axis='resentment',
    )
    reset_control_command_classifier()

    marginal_policy_calls = {'count': 0}

    def policy_marginal(*, request):
        marginal_policy_calls['count'] += 1
        return {
            'command_name': 'repair_meta_friction',
            'confidence': 0.99,
            'reason': 'should_not_happen',
            'kb_posture': 'skip_kb',
        }

    set_control_command_classifier(policy_marginal)
    policy_marginal_update = infer_dialogue_update(
        'Напиши код на python для телеграм-бота',
        dialogue_act='open_topic',
        dialogue_state={},
        dialogue_frame=DialogueFrame().as_dict(),
    )
    reset_control_command_classifier()

    def low_conf_marginal(*, request):
        return {
            'command_name': 'repair_meta_friction',
            'confidence': 0.41,
            'reason': 'uncertain_repair',
            'kb_posture': 'skip_kb',
        }

    set_control_command_classifier(low_conf_marginal)
    low_conf_marginal_update = infer_dialogue_update(
        'Так разговора у нас не получится',
        dialogue_act='open_topic',
        dialogue_state={'active_topic': 'general'},
        dialogue_frame=DialogueFrame().as_dict(),
    )
    reset_control_command_classifier()

    def invalid_marginal(*, request):
        return {
            'command_name': 'invented_command',
            'confidence': 0.97,
            'reason': 'bad_output',
            'kb_posture': 'skip_kb',
        }

    set_control_command_classifier(invalid_marginal)
    invalid_marginal_update = infer_dialogue_update(
        'Так разговора у нас не получится',
        dialogue_act='open_topic',
        dialogue_state={'active_topic': 'general'},
        dialogue_frame=DialogueFrame().as_dict(),
    )
    reset_control_command_classifier()

    with temp_store() as store:
        set_control_command_classifier(control_command)
        special_plan = planner.build_answer_plan(
            'Так разговора у нас не получится',
            user_id='marginal-router-regression',
            store=store,
            purpose='response',
            record_user_reply=False,
        )
        reset_control_command_classifier()

    original_autoload_attempted = planner._classifier_autoload_attempted
    original_mode_classifier = planner._mode_classifier
    original_kb_classifier = planner._kb_classifier
    planner._classifier_autoload_attempted = True

    def exploding_mode(question: str):
        raise RuntimeError('boom')

    planner.set_mode_classifier(exploding_mode)
    mode, mode_meta = planner.detect_mode_with_metadata('Что делать дальше?')

    kb_calls = {'count': 0}

    def kb_hook(question: str):
        kb_calls['count'] += 1
        return False

    planner.set_kb_classifier(kb_hook)
    kb_use, kb_meta = planner.should_use_kb_with_metadata('Что делать дальше?')
    blocked_use, blocked_meta = planner.should_use_kb_with_metadata('Напиши код на python для телеграм-бота')

    planner._mode_classifier = original_mode_classifier
    planner._kb_classifier = original_kb_classifier
    planner._classifier_autoload_attempted = original_autoload_attempted

    results = [
        {
            'name': 'shortlist_contains_scored_candidates',
            'pass': (
                len(shortlist) >= 1
                and shortlist[0].get('topic_candidate') == 'social-small-talk'
            ),
        },
        {
            'name': 'family_classifier_can_override_deterministic_guess',
            'pass': (
                override_update.topic_candidate == 'appearance-self-presentation'
                and override_update.update_source == 'family_classifier'
                and override_update.classifier_metadata.get('family_classifier_status') == 'accepted'
            ),
        },
        {
            'name': 'low_confidence_family_classifier_falls_back',
            'pass': (
                low_conf_update.topic_candidate == ''
                and low_conf_update.update_source == 'dialogue_act_fallback'
                and low_conf_update.classifier_metadata.get('family_classifier_rejection_reason') == 'low_confidence'
            ),
        },
        {
            'name': 'invalid_topic_from_classifier_is_rejected',
            'pass': (
                invalid_topic_update.topic_candidate == ''
                and invalid_topic_update.update_source == 'dialogue_act_fallback'
                and invalid_topic_update.classifier_metadata.get('family_classifier_rejection_reason') == 'invalid_topic'
            ),
        },
        {
            'name': 'slot_followup_never_calls_family_classifier',
            'pass': (
                slot_calls['count'] == 0
                and slot_update.transition_kind == 'axis_answer'
                and slot_update.classifier_metadata.get('family_classifier_status', '') in {'', 'not_applicable'}
            ),
        },
        {
            'name': 'policy_blocked_turn_never_calls_family_classifier',
            'pass': (
                policy_calls['count'] == 0
                and policy_update.classifier_metadata.get('family_classifier_status') == 'not_applicable'
            ),
        },
        {
            'name': 'control_command_routes_repair_and_recovery_turns',
            'pass': (
                repair_update.topic_candidate == 'repair-misunderstanding'
                and friction_update.topic_candidate == 'repair-meta-friction'
                and level_update.topic_candidate == 'repair-wrong-level'
                and vague_update.topic_candidate == 'problem-sharing-opening'
                and symptom_update.topic_candidate == 'self-diagnosis'
                and scope_update.topic_candidate == 'scope-shift-meta'
                and relationship_update.topic_candidate == 'relationship-opening-broad'
                and teasing_update.topic_candidate == 'social-small-talk'
                and repair_update.update_source == 'control_command'
                and repair_update.classifier_metadata.get('control_command_status') == 'accepted'
            ),
        },
        {
            'name': 'slot_followup_and_policy_turns_bypass_control_command',
            'pass': (
                marginal_slot_calls['count'] == 0
                and marginal_slot_update.transition_kind == 'axis_answer'
                and marginal_slot_update.update_source == 'slot_answer'
                and marginal_policy_calls['count'] == 0
                and policy_marginal_update.update_source != 'control_command'
            ),
        },
        {
            'name': 'low_confidence_and_invalid_control_commands_fall_back_cleanly',
            'pass': (
                low_conf_marginal_update.update_source == 'control_command'
                and invalid_marginal_update.update_source == 'control_command'
                and low_conf_marginal_update.topic_candidate == 'repair-meta-friction'
                and invalid_marginal_update.topic_candidate == 'repair-meta-friction'
                and low_conf_marginal_update.classifier_metadata.get('control_command_status') == 'heuristic_fallback'
                and invalid_marginal_update.classifier_metadata.get('control_command_status') == 'heuristic_fallback'
                and low_conf_marginal_update.classifier_metadata.get('control_command_rejection_reason') == 'low_confidence'
                and invalid_marginal_update.classifier_metadata.get('control_command_rejection_reason') == 'invalid_command'
            ),
        },
        {
            'name': 'accepted_control_command_bypasses_retrieval_gate',
            'pass': (
                special_plan.use_kb is False
                and special_plan.decision.action == 'ask-clarifying-question'
                and special_plan.reason == 'Control command bypassed retrieval and rendered a direct repair/opening frame.'
                and special_plan.decision.metadata.get('clarify_profile') == 'repair-meta-friction'
                and special_plan.decision.metadata.get('control_command_status') == 'accepted'
            ),
        },
        {
            'name': 'mode_classifier_falls_back_on_exception',
            'pass': (
                mode in {'practical', 'deep'}
                and mode_meta.get('mode_classifier_status') == 'exception'
            ),
        },
        {
            'name': 'kb_classifier_respects_false_and_policy_lock',
            'pass': (
                kb_use is False
                and kb_meta.get('kb_classifier_used') is True
                and blocked_use is False
                and blocked_meta.get('kb_classifier_status') == 'policy_locked'
                and kb_calls['count'] == 1
            ),
        },
    ]
    emit_report(results)


if __name__ == '__main__':
    main()
