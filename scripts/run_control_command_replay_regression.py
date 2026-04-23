#!/usr/bin/env python3
from __future__ import annotations

from _helpers import emit_report, temp_store
from library._core.runtime import planner


def main() -> None:
    with temp_store() as store:
        social = planner.build_answer_plan(
            'Добрый вечер',
            user_id='control-replay-social',
            store=store,
            purpose='response',
            record_user_reply=False,
        )
        broad_help = planner.build_answer_plan(
            'Помогите мне наладить жизнь',
            user_id='control-replay-broad-help',
            store=store,
            purpose='response',
            record_user_reply=False,
        )
        kb_grounded = planner.build_answer_plan(
            'В какой книге у Питерсона есть мысль про добровольное принятие ответственности?',
            user_id='control-replay-kb',
            store=store,
            purpose='response',
            record_user_reply=False,
        )
        repair_seed = planner.build_answer_plan(
            'Давай обсудим отношения',
            user_id='control-replay-repair',
            store=store,
            purpose='response',
            record_user_reply=False,
        )
        repair = planner.build_answer_plan(
            'Я не понимаю о чём ты',
            user_id='control-replay-repair',
            store=store,
            purpose='response',
            record_user_reply=False,
        )
        friction = planner.build_answer_plan(
            'Так разговора у нас не получится',
            user_id='control-replay-friction',
            store=store,
            purpose='response',
            record_user_reply=False,
        )
        scope_shift = planner.build_answer_plan(
            'Я имею в виду в общем',
            user_id='control-replay-scope',
            store=store,
            purpose='response',
            record_user_reply=False,
        )
        symptom = planner.build_answer_plan(
            'я подозреваю, что у меня ангедония',
            user_id='control-replay-symptom',
            store=store,
            purpose='response',
            record_user_reply=False,
        )

    social_meta = social.decision.metadata
    broad_help_meta = broad_help.decision.metadata
    kb_meta = kb_grounded.decision.metadata
    repair_meta = repair.decision.metadata
    friction_meta = friction.decision.metadata
    scope_meta = scope_shift.decision.metadata
    symptom_meta = symptom.decision.metadata

    results = [
        {
            'name': 'social_opening_uses_control_command_without_kb',
            'pass': (
                social.decision.action == 'ask-clarifying-question'
                and social.use_kb is False
                and social_meta.get('control_command_name') == 'start_social_opening'
                and social_meta.get('clarify_reason_code') in {'greeting-opening', 'social-small-talk'}
            ),
        },
        {
            'name': 'broad_help_avoids_source_lookup',
            'pass': (
                broad_help.decision.action == 'ask-clarifying-question'
                and broad_help.use_kb is False
                and broad_help_meta.get('control_command_name') == 'start_broad_help_opening'
                and broad_help_meta.get('clarify_reason_code') in {'problem-sharing-opening', 'life-direction-opening'}
                and broad_help_meta.get('clarify_reason_code') != 'source-lookup'
            ),
        },
        {
            'name': 'explicit_peterson_question_requires_kb',
            'pass': (
                kb_grounded.use_kb is True
                and kb_meta.get('control_command_name') == 'request_kb_grounding'
                and kb_meta.get('control_command_kb_posture') == 'require_kb'
            ),
        },
        {
            'name': 'repair_turn_uses_recovery_flow',
            'pass': (
                repair.decision.action == 'ask-clarifying-question'
                and repair.use_kb is False
                and repair_meta.get('control_command_name') == 'repair_misunderstanding'
                and repair_meta.get('clarify_reason_code') == 'repair-misunderstanding'
                and repair_meta.get('recovery_state_after') == 'recent_misunderstanding'
            ),
        },
        {
            'name': 'meta_friction_turn_uses_recovery_flow',
            'pass': (
                friction.decision.action == 'ask-clarifying-question'
                and friction.use_kb is False
                and friction_meta.get('control_command_name') == 'repair_meta_friction'
                and friction_meta.get('clarify_reason_code') == 'repair-meta-friction'
                and friction_meta.get('recovery_state_after') == 'recent_meta_friction'
            ),
        },
        {
            'name': 'scope_shift_turn_reframes_without_kb',
            'pass': (
                scope_shift.use_kb is False
                and scope_meta.get('control_command_name') == 'shift_scope_more_general'
                and scope_meta.get('clarify_reason_code') == 'scope-shift-meta'
            ),
        },
        {
            'name': 'symptom_self_report_avoids_source_lookup',
            'pass': (
                symptom.use_kb is False
                and symptom_meta.get('control_command_name') == 'start_symptom_self_report_opening'
                and symptom_meta.get('clarify_reason_code') == 'self-diagnosis-soft'
            ),
        },
        {
            'name': 'repair_seed_stays_non_kb',
            'pass': (
                repair_seed.use_kb is False
                and repair_seed.decision.metadata.get('control_command_name') == 'start_relationship_broad_opening'
            ),
        },
    ]
    emit_report(results)


if __name__ == '__main__':
    main()
