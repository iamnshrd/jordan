#!/usr/bin/env python3
from __future__ import annotations

from _helpers import emit_report
from library._core.runtime.dialogue_family_registry import build_dialogue_family_candidates
from library._core.runtime.dialogue_update import infer_dialogue_update
from library._core.runtime.dialogue_frame import DialogueFrame
from library._core.runtime.llm_classifiers import reset_family_classifier, set_family_classifier
from library._core.runtime import planner


def main() -> None:
    shortlist = build_dialogue_family_candidates('Проверяем рендерер')

    def override_family(*, request):
        return {
            'topic_candidate': 'social-small-talk',
            'route_candidate': 'general',
            'stance_shift': 'general',
            'goal_candidate': 'opening',
            'confidence': 0.96,
            'reason': 'meta_opening',
        }

    set_family_classifier(override_family)
    override_update = infer_dialogue_update(
        'Проверяем рендерер',
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

    def low_conf_family(*, request):
        return {
            'topic_candidate': 'social-small-talk',
            'route_candidate': 'general',
            'stance_shift': 'general',
            'goal_candidate': 'opening',
            'confidence': 0.42,
            'reason': 'uncertain_guess',
        }

    set_family_classifier(low_conf_family)
    low_conf_update = infer_dialogue_update(
        'Проверяем рендерер',
        dialogue_act='open_topic',
        dialogue_state={},
        dialogue_frame=DialogueFrame().as_dict(),
    )
    reset_family_classifier()

    def invalid_topic_family(*, request):
        return {
            'topic_candidate': 'invented-topic',
            'route_candidate': 'general',
            'stance_shift': 'general',
            'goal_candidate': 'opening',
            'confidence': 0.98,
            'reason': 'bad_output',
        }

    set_family_classifier(invalid_topic_family)
    invalid_topic_update = infer_dialogue_update(
        'Проверяем рендерер',
        dialogue_act='open_topic',
        dialogue_state={},
        dialogue_frame=DialogueFrame().as_dict(),
    )
    reset_family_classifier()

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
                override_update.topic_candidate == 'social-small-talk'
                and override_update.update_source == 'family_classifier'
                and override_update.classifier_metadata.get('family_classifier_status') == 'accepted'
            ),
        },
        {
            'name': 'low_confidence_family_classifier_falls_back',
            'pass': (
                low_conf_update.topic_candidate == 'social-small-talk'
                and low_conf_update.classifier_metadata.get('family_classifier_rejection_reason') == 'low_confidence'
            ),
        },
        {
            'name': 'invalid_topic_from_classifier_is_rejected',
            'pass': (
                invalid_topic_update.topic_candidate == 'social-small-talk'
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
