#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import uuid

from _helpers import REPO_ROOT, emit_report


def _parse_payload(stdout: str) -> dict:
    lines = [line for line in stdout.splitlines() if line.strip()]
    for candidate in reversed(lines):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return {}


def _run_adapter(question: str, user_id: str) -> tuple[int, dict, str]:
    proc = subprocess.run(
        [
            sys.executable,
            '-m',
            'library',
            '--user-id',
            user_id,
            'adapter',
            'telegram',
            question,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode, _parse_payload(proc.stdout), proc.stderr.strip()


def main() -> None:
    user_id = f"telegram:dialogue-{uuid.uuid4().hex[:8]}"

    first_rc, first_payload, first_stderr = _run_adapter(
        'Какие могут быть причины потери чувств в серьезных отношениях?',
        user_id,
    )
    second_rc, second_payload, second_stderr = _run_adapter(
        'Я имею ввиду абстрактно, не конкретно у меня',
        user_id,
    )
    third_rc, third_payload, third_stderr = _run_adapter(
        'да, в общем виде',
        user_id,
    )
    fourth_rc, fourth_payload, fourth_stderr = _run_adapter(
        'скорее обида',
        user_id,
    )
    fifth_rc, fifth_payload, fifth_stderr = _run_adapter(
        'скорее из унижения',
        user_id,
    )
    sixth_rc, sixth_payload, sixth_stderr = _run_adapter(
        'и что это значит?',
        user_id,
    )
    seventh_rc, seventh_payload, seventh_stderr = _run_adapter(
        'и что с этим делать?',
        user_id,
    )
    eighth_rc, eighth_payload, eighth_stderr = _run_adapter(
        'приведи пример',
        user_id,
    )
    ninth_rc, ninth_payload, ninth_stderr = _run_adapter(
        'ладно, другой вопрос: я подозреваю, что у меня ангедония',
        user_id,
    )

    first_meta = first_payload.get('decision_metadata') or {}
    second_meta = second_payload.get('decision_metadata') or {}
    third_meta = third_payload.get('decision_metadata') or {}
    fourth_meta = fourth_payload.get('decision_metadata') or {}
    fifth_meta = fifth_payload.get('decision_metadata') or {}
    sixth_meta = sixth_payload.get('decision_metadata') or {}
    seventh_meta = seventh_payload.get('decision_metadata') or {}
    eighth_meta = eighth_payload.get('decision_metadata') or {}
    ninth_meta = ninth_payload.get('decision_metadata') or {}

    results = [
        {
            'name': 'first_turn_opens_relationship_loss_topic',
            'pass': (
                first_rc == 0
                and first_payload.get('reason_code') == 'relationship-knot'
                and first_meta.get('active_topic') == 'relationship-loss-of-feeling'
                and first_meta.get('dialogue_mode') == 'human_problem_clarify'
            ),
        },
        {
            'name': 'abstract_followup_reuses_topic_instead_of_resetting',
            'pass': (
                second_rc == 0
                and second_payload.get('decision_type') == 'clarify'
                and second_payload.get('reason_code') == 'abstractify-relationship-loss-of-feeling'
                and second_meta.get('dialogue_act') == 'abstractify_previous_question'
                and second_meta.get('active_topic') == 'relationship-loss-of-feeling'
                and second_meta.get('abstraction_level') == 'general'
                and second_meta.get('topic_reused') is True
                and second_meta.get('response_move') == 'acknowledge_and_continue'
                and 'речь теперь не о твоём частном случае' in (
                    second_payload.get('final_user_text') or ''
                ).lower()
                and 'астролог' not in (second_payload.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'confirm_scope_keeps_general_relationship_thread_alive',
            'pass': (
                third_rc == 0
                and third_payload.get('decision_type') == 'clarify'
                and third_payload.get('reason_code') == 'abstractify-relationship-loss-of-feeling'
                and third_meta.get('dialogue_act') == 'confirm_scope'
                and third_meta.get('active_topic') == 'relationship-loss-of-feeling'
                and third_meta.get('abstraction_level') == 'general'
                and 'чувство в серьёзных отношениях редко умирает по одной причине' in (
                    third_payload.get('final_user_text') or ''
                ).lower()
            ),
        },
        {
            'name': 'axis_followup_keeps_relationship_thread_and_advances_it',
            'pass': (
                fourth_rc == 0
                and fourth_payload.get('decision_type') == 'clarify'
                and fourth_payload.get('reason_code') == 'relationship-loss-of-feeling-axis-followup'
                and fourth_meta.get('dialogue_act') == 'supply_narrowing_axis'
                and fourth_meta.get('active_topic') == 'relationship-loss-of-feeling'
                and fourth_meta.get('dialogue_mode') == 'followup_narrowing'
                and fourth_meta.get('active_axis') == 'resentment'
                and fourth_meta.get('selected_axis') == 'resentment'
                and fourth_meta.get('topic_reused') is True
                and 'главный разрушитель здесь обида' in (
                    fourth_payload.get('final_user_text') or ''
                ).lower()
            ),
        },
        {
            'name': 'detail_followup_deepens_same_relationship_thread',
            'pass': (
                fifth_rc == 0
                and fifth_payload.get('decision_type') == 'clarify'
                and fifth_payload.get('reason_code') == 'relationship-loss-of-feeling-detail-followup'
                and fifth_meta.get('dialogue_act') == 'supply_concrete_manifestation'
                and fifth_meta.get('active_topic') == 'relationship-loss-of-feeling'
                and fifth_meta.get('dialogue_mode') == 'followup_deepen'
                and fifth_meta.get('active_axis') == 'resentment'
                and fifth_meta.get('active_detail') == 'humiliation'
                and fifth_meta.get('selected_detail') == 'humiliation'
                and fifth_meta.get('topic_reused') is True
                and 'достоинство' in (fifth_payload.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'mini_analysis_reuses_detail_and_explains_pattern',
            'pass': (
                sixth_rc == 0
                and sixth_payload.get('decision_type') == 'clarify'
                and sixth_payload.get('reason_code') == 'relationship-loss-of-feeling-mini-analysis'
                and sixth_meta.get('dialogue_act') == 'request_mini_analysis'
                and sixth_meta.get('dialogue_mode') == 'mini_analysis'
                and sixth_meta.get('active_topic') == 'relationship-loss-of-feeling'
                and sixth_meta.get('active_axis') == 'resentment'
                and sixth_meta.get('active_detail') == 'humiliation'
                and sixth_meta.get('topic_reused') is True
                and sixth_meta.get('response_move') == 'acknowledge_and_continue'
                and 'если держаться именно этого узла' in (
                    sixth_payload.get('final_user_text') or ''
                ).lower()
                and 'удар по достоинству' in (sixth_payload.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'next_step_reuses_same_relationship_thread_and_turns_practical',
            'pass': (
                seventh_rc == 0
                and seventh_payload.get('decision_type') == 'clarify'
                and seventh_payload.get('reason_code') == 'relationship-loss-of-feeling-next-step'
                and seventh_meta.get('dialogue_act') == 'request_next_step'
                and seventh_meta.get('dialogue_mode') == 'practical_next_step'
                and seventh_meta.get('active_topic') == 'relationship-loss-of-feeling'
                and seventh_meta.get('active_axis') == 'resentment'
                and seventh_meta.get('active_detail') == 'humiliation'
                and seventh_meta.get('topic_reused') is True
                and seventh_meta.get('response_move') == 'acknowledge_and_continue'
                and 'не будем снова расширять тему' in (
                    seventh_payload.get('final_user_text') or ''
                ).lower()
                and 'один прямой разговор' in (seventh_payload.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'example_followup_keeps_same_relationship_thread_and_illustrates_pattern',
            'pass': (
                eighth_rc == 0
                and eighth_payload.get('decision_type') == 'clarify'
                and eighth_payload.get('reason_code') == 'relationship-loss-of-feeling-example'
                and eighth_meta.get('dialogue_act') == 'request_example'
                and eighth_meta.get('dialogue_mode') == 'example_illustration'
                and eighth_meta.get('active_topic') == 'relationship-loss-of-feeling'
                and eighth_meta.get('active_axis') == 'resentment'
                and eighth_meta.get('active_detail') == 'humiliation'
                and eighth_meta.get('topic_reused') is True
                and eighth_meta.get('response_move') == 'acknowledge_and_continue'
                and 'не останемся на уровне схемы' in (eighth_payload.get('final_user_text') or '').lower()
                and 'шутит или говорит с пренебрежением' in (eighth_payload.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'topic_shift_closes_relationship_thread_and_opens_self_diagnosis_cleanly',
            'pass': (
                ninth_rc == 0
                and ninth_payload.get('decision_type') == 'clarify'
                and ninth_payload.get('reason_code') == 'self-diagnosis-soft'
                and ninth_meta.get('dialogue_act') == 'topic_shift'
                and ninth_meta.get('active_topic') == 'self-diagnosis'
                and ninth_meta.get('dialogue_mode') == 'human_problem_clarify'
                and ninth_meta.get('pending_slot') == 'symptom_narrowing'
                and ninth_meta.get('topic_reused') is False
                and ninth_meta.get('response_move') == 'acknowledge_and_continue'
                and 'оставим прежний узел' in (ninth_payload.get('final_user_text') or '').lower()
                and 'диагноз' in (ninth_payload.get('final_user_text') or '').lower()
            ),
        },
    ]

    emit_report(
        results,
        samples={
            'first_turn': first_payload,
            'abstract_followup': second_payload,
            'confirm_scope': third_payload,
            'axis_followup': fourth_payload,
            'detail_followup': fifth_payload,
            'mini_analysis': sixth_payload,
            'next_step': seventh_payload,
            'example': eighth_payload,
            'topic_shift': ninth_payload,
        },
        stderr={
            'first_turn': first_stderr,
            'abstract_followup': second_stderr,
            'confirm_scope': third_stderr,
            'axis_followup': fourth_stderr,
            'detail_followup': fifth_stderr,
            'mini_analysis': sixth_stderr,
            'next_step': seventh_stderr,
            'example': eighth_stderr,
            'topic_shift': ninth_stderr,
        },
    )


if __name__ == '__main__':
    main()
