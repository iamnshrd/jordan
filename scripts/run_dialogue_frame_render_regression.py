#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from _helpers import emit_report
from library._core.runtime.clarify_human import build_clarification


def main() -> None:
    general_relationship = build_clarification(
        'Я имею ввиду абстрактно, не конкретно у меня',
        dialogue_state={
            'active_topic': 'relationship-loss-of-feeling',
            'active_route': 'relationship-maintenance',
            'abstraction_level': 'personal',
            'pending_slot': 'narrowing_axis',
            'active_axis': '',
            'active_detail': '',
        },
        dialogue_frame={
            'topic': 'relationship-loss-of-feeling',
            'route': 'relationship-maintenance',
            'frame_type': 'relationship_problem',
            'stance': 'general',
            'goal': 'overview',
            'axis': '',
            'detail': '',
            'pending_slot': 'pattern_family',
            'relation_to_previous': 'reframe',
            'confidence': '0.9',
        },
        dialogue_act='open_topic',
    )
    next_step = build_clarification(
        'и что с этим делать?',
        dialogue_state={
            'active_topic': 'relationship-loss-of-feeling',
            'active_route': 'relationship-maintenance',
            'abstraction_level': 'personal',
            'pending_slot': 'next_step',
            'active_axis': 'resentment',
            'active_detail': 'humiliation',
        },
        dialogue_frame={
            'topic': 'relationship-loss-of-feeling',
            'route': 'relationship-maintenance',
            'frame_type': 'relationship_problem',
            'stance': 'personal',
            'goal': 'next_step',
            'axis': 'resentment',
            'detail': 'humiliation',
            'pending_slot': 'next_step',
            'relation_to_previous': 'continue',
            'confidence': '0.9',
        },
        dialogue_act='open_topic',
    )
    self_diagnosis = build_clarification(
        'я подозреваю, что у меня ангедония',
        dialogue_state={
            'active_topic': '',
            'active_route': 'general',
            'abstraction_level': 'personal',
            'pending_slot': '',
            'active_axis': '',
            'active_detail': '',
        },
        dialogue_frame={
            'topic': 'self-diagnosis',
            'route': 'general',
            'frame_type': 'self_diagnosis_soft',
            'stance': 'personal',
            'goal': 'clarify',
            'axis': '',
            'detail': '',
            'pending_slot': 'symptom_narrowing',
            'relation_to_previous': 'shift',
            'confidence': '0.9',
        },
        dialogue_act='open_topic',
    )
    lost_and_aimless = build_clarification(
        'я потерял смысл и направление',
        dialogue_state={
            'active_topic': '',
            'active_route': 'career-vocation',
            'abstraction_level': 'personal',
            'pending_slot': '',
            'active_axis': '',
            'active_detail': '',
        },
        dialogue_frame={
            'topic': 'lost-and-aimless',
            'route': 'career-vocation',
            'frame_type': 'meaning_direction',
            'stance': 'personal',
            'goal': 'clarify',
            'axis': '',
            'detail': '',
            'pending_slot': 'narrowing_axis',
            'relation_to_previous': 'new',
            'confidence': '0.9',
        },
        dialogue_act='open_topic',
    )
    portrait = build_clarification(
        'давай составим мой психологический портрет',
        dialogue_state={
            'active_topic': '',
            'active_route': 'general',
            'abstraction_level': 'personal',
            'pending_slot': '',
            'active_axis': '',
            'active_detail': '',
        },
        dialogue_frame={
            'topic': 'psychological-portrait',
            'route': 'general',
            'frame_type': 'portrait_request',
            'stance': 'personal',
            'goal': 'clarify',
            'axis': '',
            'detail': '',
            'pending_slot': 'pattern_selection',
            'relation_to_previous': 'new',
            'confidence': '0.82',
        },
        dialogue_act='open_topic',
    )
    relationship_foundations = build_clarification(
        'В чем заключается суть крепких отношений?',
        dialogue_state={
            'active_topic': '',
            'active_route': 'relationship-maintenance',
            'abstraction_level': 'general',
            'pending_slot': '',
            'active_axis': '',
            'active_detail': '',
        },
        dialogue_frame={
            'topic': 'relationship-foundations',
            'route': 'relationship-maintenance',
            'frame_type': 'relationship_foundations',
            'stance': 'general',
            'goal': 'overview',
            'axis': '',
            'detail': '',
            'pending_slot': 'pattern_family',
            'relation_to_previous': 'new',
            'confidence': '0.9',
        },
        dialogue_act='open_topic',
    )
    scope_menu = build_clarification(
        'На какие темы с тобой можно говорить?',
        dialogue_state={
            'active_topic': '',
            'active_route': 'general',
            'abstraction_level': 'general',
            'pending_slot': '',
            'active_axis': '',
            'active_detail': '',
        },
        dialogue_frame={
            'topic': 'scope-topics',
            'route': 'general',
            'frame_type': 'scope_menu',
            'stance': 'general',
            'goal': 'menu',
            'axis': '',
            'detail': '',
            'pending_slot': 'topic_selection',
            'relation_to_previous': 'new',
            'confidence': '0.9',
        },
        dialogue_act='open_topic',
    )
    self_evaluation = build_clarification(
        'Что со мной не так?',
        dialogue_state={
            'active_topic': '',
            'active_route': 'general',
            'abstraction_level': 'personal',
            'pending_slot': '',
            'active_axis': '',
            'active_detail': '',
        },
        dialogue_frame={
            'topic': 'self-evaluation',
            'route': 'general',
            'frame_type': 'self_inquiry',
            'stance': 'personal',
            'goal': 'clarify',
            'axis': '',
            'detail': '',
            'pending_slot': 'pattern_selection',
            'relation_to_previous': 'new',
            'confidence': '0.9',
        },
        dialogue_act='open_topic',
    )
    shame_self_contempt = build_clarification(
        'Мне стыдно за себя целиком',
        dialogue_state={
            'active_topic': '',
            'active_route': 'shame-self-contempt',
            'abstraction_level': 'personal',
            'pending_slot': '',
            'active_axis': '',
            'active_detail': '',
        },
        dialogue_frame={
            'topic': 'shame-self-contempt',
            'route': 'shame-self-contempt',
            'frame_type': 'shame_self_contempt',
            'stance': 'personal',
            'goal': 'clarify',
            'axis': '',
            'detail': '',
            'pending_slot': 'narrowing_axis',
            'relation_to_previous': 'new',
            'confidence': '0.9',
        },
        dialogue_act='open_topic',
    )

    results = [
        {
            'name': 'frame_overview_dispatches_without_matching_dialogue_act',
            'pass': (
                general_relationship.metadata.get('clarify_profile') == 'abstractify-relationship-loss-of-feeling'
                and general_relationship.metadata.get('response_move') == 'acknowledge_and_continue'
                and 'речь теперь не о твоём частном случае' in general_relationship.text.lower()
            ),
        },
        {
            'name': 'frame_next_step_dispatches_without_matching_dialogue_act',
            'pass': (
                next_step.metadata.get('clarify_profile') == 'next-step'
                and next_step.metadata.get('response_move') == 'acknowledge_and_continue'
                and 'не будем снова расширять тему' in next_step.text.lower()
            ),
        },
        {
            'name': 'frame_self_diagnosis_opening_dispatches_without_matching_dialogue_act',
            'pass': (
                self_diagnosis.metadata.get('clarify_reason_code') == 'self-diagnosis-soft'
                and self_diagnosis.metadata.get('clarify_question_kind') == 'symptom_narrowing'
                and 'диагноз' in self_diagnosis.text.lower()
            ),
        },
        {
            'name': 'frame_lost_and_aimless_opening_dispatches_without_matching_dialogue_act',
            'pass': (
                lost_and_aimless.metadata.get('clarify_reason_code') == 'lost-and-aimless'
                and lost_and_aimless.metadata.get('clarify_question_kind') == 'narrowing'
                and 'растерян' in lost_and_aimless.text.lower()
            ),
        },
        {
            'name': 'frame_portrait_opening_dispatches_without_matching_dialogue_act',
            'pass': (
                portrait.metadata.get('clarify_reason_code') == 'psychological-portrait-request'
                and portrait.metadata.get('clarify_question_kind') == 'pattern_selection'
                and 'психологический портрет' in portrait.text.lower()
            ),
        },
        {
            'name': 'frame_relationship_foundations_overview_dispatches_without_matching_dialogue_act',
            'pass': (
                relationship_foundations.metadata.get('clarify_reason_code') == 'relationship-foundations-overview'
                and relationship_foundations.metadata.get('clarify_question_kind') == 'topic_variant'
                and 'крепких отношениях' in relationship_foundations.text.lower()
            ),
        },
        {
            'name': 'frame_scope_menu_dispatches_without_matching_dialogue_act',
            'pass': (
                scope_menu.metadata.get('clarify_reason_code') == 'scope-topics'
                and scope_menu.metadata.get('clarify_question_kind') == 'topic_selection'
                and 'смысл и направление' in scope_menu.text.lower()
            ),
        },
        {
            'name': 'frame_self_evaluation_dispatches_without_matching_dialogue_act',
            'pass': (
                self_evaluation.metadata.get('clarify_reason_code') == 'self-evaluation-request'
                and self_evaluation.metadata.get('clarify_question_kind') == 'pattern_selection'
                and 'ярлык' in self_evaluation.text.lower()
            ),
        },
        {
            'name': 'frame_shame_self_contempt_dispatches_without_matching_dialogue_act',
            'pass': (
                shame_self_contempt.metadata.get('clarify_reason_code') == 'shame-self-contempt-request'
                and shame_self_contempt.metadata.get('clarify_question_kind') == 'narrowing'
                and 'стыд' in shame_self_contempt.text.lower()
            ),
        },
    ]

    emit_report(
        results,
        samples={
            'overview': {'text': general_relationship.text, 'metadata': general_relationship.metadata},
            'next_step': {'text': next_step.text, 'metadata': next_step.metadata},
            'self_diagnosis': {'text': self_diagnosis.text, 'metadata': self_diagnosis.metadata},
            'lost_and_aimless': {'text': lost_and_aimless.text, 'metadata': lost_and_aimless.metadata},
            'portrait': {'text': portrait.text, 'metadata': portrait.metadata},
            'relationship_foundations': {'text': relationship_foundations.text, 'metadata': relationship_foundations.metadata},
            'scope_menu': {'text': scope_menu.text, 'metadata': scope_menu.metadata},
            'self_evaluation': {'text': self_evaluation.text, 'metadata': self_evaluation.metadata},
            'shame_self_contempt': {'text': shame_self_contempt.text, 'metadata': shame_self_contempt.metadata},
        },
    )
