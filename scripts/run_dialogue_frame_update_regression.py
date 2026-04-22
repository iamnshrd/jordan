#!/usr/bin/env python3
from __future__ import annotations

from _helpers import emit_report
from library._core.runtime.dialogue_update import apply_dialogue_update, infer_dialogue_update


def _relationship_general_state() -> tuple[dict, dict]:
    state = {
        'active_topic': 'relationship-loss-of-feeling',
        'active_route': 'relationship-maintenance',
        'dialogue_mode': 'followup_reframe',
        'abstraction_level': 'general',
        'pending_slot': 'pattern_family',
        'active_axis': '',
        'active_detail': '',
    }
    frame = {
        'version': 1,
        'topic': 'relationship-loss-of-feeling',
        'route': 'relationship-maintenance',
        'frame_type': 'relationship_general',
        'stance': 'general',
        'goal': 'overview',
        'axis': '',
        'detail': '',
        'pending_slot': 'pattern_family',
        'relation_to_previous': 'reframe',
        'confidence': '0.9',
    }
    return state, frame


def _self_diagnosis_state() -> tuple[dict, dict]:
    state = {
        'active_topic': 'self-diagnosis',
        'active_route': 'general',
        'dialogue_mode': 'human_problem_clarify',
        'abstraction_level': 'personal',
        'pending_slot': 'symptom_narrowing',
        'active_axis': '',
        'active_detail': '',
    }
    frame = {
        'version': 1,
        'topic': 'self-diagnosis',
        'route': 'general',
        'frame_type': 'self_diagnosis_soft',
        'stance': 'personal',
        'goal': 'clarify',
        'axis': '',
        'detail': '',
        'pending_slot': 'symptom_narrowing',
        'relation_to_previous': 'new',
        'confidence': '0.82',
    }
    return state, frame


def main() -> None:
    rel_state, rel_frame = _relationship_general_state()
    self_state, self_frame = _self_diagnosis_state()

    cause_update = infer_dialogue_update(
        'какие основные причины?',
        dialogue_act='open_topic',
        dialogue_state=rel_state,
        dialogue_frame=rel_frame,
    )
    cause_frame = apply_dialogue_update(rel_frame, cause_update, fallback_state=rel_state).as_dict()

    personalize_update = infer_dialogue_update(
        'а если у меня лично?',
        dialogue_act='open_topic',
        dialogue_state=rel_state,
        dialogue_frame=rel_frame,
    )
    personalize_frame = apply_dialogue_update(rel_frame, personalize_update, fallback_state=rel_state).as_dict()

    shift_update = infer_dialogue_update(
        'ладно, другой вопрос: я подозреваю, что у меня ангедония',
        dialogue_act='open_topic',
        dialogue_state=rel_state,
        dialogue_frame=rel_frame,
    )
    shift_frame = apply_dialogue_update(rel_frame, shift_update, fallback_state=rel_state).as_dict()

    axis_update = infer_dialogue_update(
        'скорее пустота',
        dialogue_act='open_topic',
        dialogue_state=self_state,
        dialogue_frame=self_frame,
    )
    axis_frame = apply_dialogue_update(self_frame, axis_update, fallback_state=self_state).as_dict()

    menu_update = infer_dialogue_update(
        'Что мы можем обсудить?',
        dialogue_act='open_topic',
        dialogue_state=rel_state,
        dialogue_frame=rel_frame,
    )
    menu_frame = apply_dialogue_update(rel_frame, menu_update, fallback_state=rel_state).as_dict()

    self_eval_update = infer_dialogue_update(
        'Что со мной не так?',
        dialogue_act='open_topic',
        dialogue_state=rel_state,
        dialogue_frame=rel_frame,
    )
    self_eval_frame = apply_dialogue_update(rel_frame, self_eval_update, fallback_state=rel_state).as_dict()

    shame_update = infer_dialogue_update(
        'Мне стыдно за себя целиком',
        dialogue_act='open_topic',
        dialogue_state=rel_state,
        dialogue_frame=rel_frame,
    )
    shame_frame = apply_dialogue_update(rel_frame, shame_update, fallback_state=rel_state).as_dict()

    semantic_foundations_update = infer_dialogue_update(
        'Из чего строится по-настоящему крепкий брак?',
        dialogue_act='open_topic',
        dialogue_state=rel_state,
        dialogue_frame=rel_frame,
    )
    semantic_foundations_frame = apply_dialogue_update(
        rel_frame,
        semantic_foundations_update,
        fallback_state=rel_state,
    ).as_dict()
    stale_slot_topic_update = infer_dialogue_update(
        'В чем заключается смысл крепких отношений?',
        dialogue_act='open_topic',
        dialogue_state=self_state,
        dialogue_frame=self_frame,
    )
    stale_slot_topic_frame = apply_dialogue_update(
        self_frame,
        stale_slot_topic_update,
        fallback_state=self_state,
    ).as_dict()
    foundations_state = {
        'active_topic': 'relationship-foundations',
        'active_route': 'relationship-maintenance',
        'dialogue_mode': 'example_illustration',
        'abstraction_level': 'general',
        'pending_slot': 'pattern_family',
        'active_axis': '',
        'active_detail': '',
    }
    foundations_frame = {
        'version': 1,
        'topic': 'relationship-foundations',
        'route': 'relationship-maintenance',
        'frame_type': 'relationship_foundations',
        'stance': 'general',
        'goal': 'example',
        'axis': '',
        'detail': '',
        'pending_slot': 'pattern_family',
        'relation_to_previous': 'continue',
        'confidence': '0.9',
    }
    foundations_axis_update = infer_dialogue_update(
        'скорее обида',
        dialogue_act='open_topic',
        dialogue_state=foundations_state,
        dialogue_frame=foundations_frame,
    )
    foundations_axis_frame = apply_dialogue_update(
        foundations_frame,
        foundations_axis_update,
        fallback_state=foundations_state,
    ).as_dict()
    foundations_detail_state = {
        **foundations_state,
        'dialogue_mode': 'followup_narrowing',
        'pending_slot': 'concrete_manifestation',
        'active_axis': 'resentment',
    }
    foundations_detail_frame = {
        **foundations_frame,
        'goal': 'clarify',
        'axis': 'resentment',
        'pending_slot': 'concrete_manifestation',
        'transition_kind': 'axis_answer',
    }
    foundations_detail_update = infer_dialogue_update(
        'скорее из унижения',
        dialogue_act='open_topic',
        dialogue_state=foundations_detail_state,
        dialogue_frame=foundations_detail_frame,
    )

    results = [
        {
            'name': 'frame_update_infers_cause_list_without_correct_act',
            'pass': (
                cause_update.goal_candidate == 'cause_list'
                and cause_update.relation_to_previous == 'continue'
                and cause_update.update_source == 'intent_registry'
                and cause_frame.get('goal') == 'cause_list'
                and cause_frame.get('topic') == 'relationship-loss-of-feeling'
            ),
        },
        {
            'name': 'frame_update_infers_personalize_without_correct_act',
            'pass': (
                personalize_update.goal_candidate == 'clarify'
                and personalize_update.relation_to_previous == 'reframe'
                and personalize_update.update_source == 'intent_registry'
                and personalize_frame.get('stance') == 'personal'
                and personalize_frame.get('topic') == 'relationship-loss-of-feeling'
            ),
        },
        {
            'name': 'frame_update_infers_topic_shift_without_correct_act',
            'pass': (
                shift_update.is_new_topic
                and shift_update.relation_to_previous == 'shift'
                and shift_update.update_source == 'intent_registry'
                and shift_frame.get('topic') == 'self-diagnosis'
                and shift_frame.get('goal') == 'clarify'
            ),
        },
        {
            'name': 'frame_update_infers_axis_answer_without_correct_act',
            'pass': (
                axis_update.relation_to_previous == 'answer_slot'
                and axis_update.goal_candidate == 'clarify'
                and axis_update.update_source == 'slot_answer'
                and axis_update.slot_fill.get('axis') == 'emotional_flatness'
                and axis_frame.get('axis') == 'emotional_flatness'
            ),
        },
        {
            'name': 'frame_update_infers_scope_menu_without_correct_act',
            'pass': (
                menu_update.is_new_topic
                and menu_update.relation_to_previous in {'new', 'shift'}
                and menu_update.update_source in {'family_registry', 'fresh_topic_guard'}
                and menu_update.topic_candidate == 'scope-topics'
                and menu_update.goal_candidate == 'menu'
                and menu_frame.get('topic') == 'scope-topics'
                and menu_frame.get('goal') == 'menu'
                and menu_frame.get('frame_type') == 'scope_menu'
                and menu_frame.get('pending_slot') == 'topic_selection'
            ),
        },
        {
            'name': 'frame_update_infers_self_evaluation_without_correct_act',
            'pass': (
                self_eval_update.is_new_topic
                and self_eval_update.relation_to_previous == 'new'
                and self_eval_update.update_source == 'family_registry'
                and self_eval_update.topic_candidate == 'self-evaluation'
                and self_eval_update.goal_candidate == 'clarify'
                and self_eval_frame.get('topic') == 'self-evaluation'
                and self_eval_frame.get('goal') == 'clarify'
                and self_eval_frame.get('frame_type') == 'self_inquiry'
            ),
        },
        {
            'name': 'frame_update_infers_shame_family_without_correct_act',
            'pass': (
                shame_update.is_new_topic
                and shame_update.relation_to_previous == 'new'
                and shame_update.update_source == 'family_registry'
                and shame_update.topic_candidate == 'shame-self-contempt'
                and shame_update.goal_candidate == 'clarify'
                and shame_frame.get('topic') == 'shame-self-contempt'
                and shame_frame.get('goal') == 'clarify'
                and shame_frame.get('frame_type') == 'shame_self_contempt'
            ),
        },
        {
            'name': 'frame_update_infers_semantic_relationship_foundations_paraphrase',
            'pass': (
                semantic_foundations_update.is_new_topic
                and semantic_foundations_update.update_source == 'family_registry'
                and semantic_foundations_update.topic_candidate == 'relationship-foundations'
                and semantic_foundations_update.goal_candidate == 'overview'
                and semantic_foundations_frame.get('topic') == 'relationship-foundations'
                and semantic_foundations_frame.get('goal') == 'overview'
                and semantic_foundations_frame.get('frame_type') == 'relationship_foundations'
            ),
        },
        {
            'name': 'new_topic_opening_beats_stale_slot_answer',
            'pass': (
                stale_slot_topic_update.is_new_topic
                and stale_slot_topic_update.update_source == 'family_registry'
                and stale_slot_topic_update.transition_kind == 'opening'
                and stale_slot_topic_update.topic_candidate == 'relationship-foundations'
                and stale_slot_topic_frame.get('topic') == 'relationship-foundations'
                and stale_slot_topic_frame.get('goal') == 'overview'
                and stale_slot_topic_frame.get('transition_kind') == 'opening'
            ),
        },
        {
            'name': 'slot_like_followup_after_foundations_example_stays_in_current_topic',
            'pass': (
                not foundations_axis_update.is_new_topic
                and foundations_axis_update.update_source == 'slot_answer'
                and foundations_axis_update.transition_kind == 'axis_answer'
                and foundations_axis_update.topic_candidate == 'relationship-foundations'
                and foundations_axis_frame.get('topic') == 'relationship-foundations'
                and foundations_axis_frame.get('axis') == 'resentment'
            ),
        },
        {
            'name': 'slot_like_detail_followup_after_foundations_axis_stays_in_current_topic',
            'pass': (
                not foundations_detail_update.is_new_topic
                and foundations_detail_update.update_source == 'slot_answer'
                and foundations_detail_update.transition_kind == 'detail_answer'
                and foundations_detail_update.topic_candidate == 'relationship-foundations'
                and foundations_detail_update.slot_fill.get('detail') == 'humiliation'
            ),
        },
    ]

    emit_report(
        results,
        samples={
            'cause_update': cause_update.as_dict(),
            'personalize_update': personalize_update.as_dict(),
            'shift_update': shift_update.as_dict(),
            'axis_update': axis_update.as_dict(),
            'menu_update': menu_update.as_dict(),
            'self_eval_update': self_eval_update.as_dict(),
            'shame_update': shame_update.as_dict(),
            'cause_frame': cause_frame,
            'personalize_frame': personalize_frame,
            'shift_frame': shift_frame,
            'axis_frame': axis_frame,
            'menu_frame': menu_frame,
            'self_eval_frame': self_eval_frame,
            'shame_frame': shame_frame,
            'semantic_foundations_update': semantic_foundations_update.as_dict(),
            'semantic_foundations_frame': semantic_foundations_frame,
            'stale_slot_topic_update': stale_slot_topic_update.as_dict(),
            'stale_slot_topic_frame': stale_slot_topic_frame,
            'foundations_axis_update': foundations_axis_update.as_dict(),
            'foundations_axis_frame': foundations_axis_frame,
            'foundations_detail_update': foundations_detail_update.as_dict(),
        },
    )


if __name__ == '__main__':
    main()
