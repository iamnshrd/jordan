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
    portrait_user = f'telegram:dialogue-portrait-{uuid.uuid4().hex[:8]}'
    diagnosis_user = f'telegram:dialogue-diagnosis-{uuid.uuid4().hex[:8]}'
    diagnosis_early_next_step_user = f'telegram:dialogue-diagnosis-earlynext-{uuid.uuid4().hex[:8]}'
    menu_user = f'telegram:dialogue-menu-{uuid.uuid4().hex[:8]}'
    self_eval_user = f'telegram:dialogue-selfeval-{uuid.uuid4().hex[:8]}'
    shame_user = f'telegram:dialogue-shame-{uuid.uuid4().hex[:8]}'
    feedback_user = f'telegram:dialogue-feedback-{uuid.uuid4().hex[:8]}'

    portrait_rc, portrait, portrait_stderr = _run_adapter(
        'Хорошо, давай тогда составим мой психологический портрет',
        portrait_user,
    )
    diagnosis_rc, diagnosis, diagnosis_stderr = _run_adapter(
        'я подозреваю, что у меня ангедония',
        diagnosis_user,
    )
    diagnosis_followup_rc, diagnosis_followup, diagnosis_followup_stderr = _run_adapter(
        'скорее пустота',
        diagnosis_user,
    )
    diagnosis_early_seed_rc, diagnosis_early_seed, diagnosis_early_seed_stderr = _run_adapter(
        'я подозреваю, что у меня ангедония',
        diagnosis_early_next_step_user,
    )
    diagnosis_early_followup_rc, diagnosis_early_followup, diagnosis_early_followup_stderr = _run_adapter(
        'скорее пустота',
        diagnosis_early_next_step_user,
    )
    diagnosis_early_next_step_rc, diagnosis_early_next_step, diagnosis_early_next_step_stderr = _run_adapter(
        'и что с этим делать?',
        diagnosis_early_next_step_user,
    )
    diagnosis_detail_rc, diagnosis_detail, diagnosis_detail_stderr = _run_adapter(
        'скорее отчуждение от людей',
        diagnosis_user,
    )
    diagnosis_analysis_rc, diagnosis_analysis, diagnosis_analysis_stderr = _run_adapter(
        'и что это значит?',
        diagnosis_user,
    )
    diagnosis_next_step_rc, diagnosis_next_step, diagnosis_next_step_stderr = _run_adapter(
        'и что с этим делать?',
        diagnosis_user,
    )
    diagnosis_example_rc, diagnosis_example, diagnosis_example_stderr = _run_adapter(
        'приведи пример',
        diagnosis_user,
    )
    menu_rc, menu, menu_stderr = _run_adapter(
        'а на что в базе есть опора, о чем можно поговорить?',
        menu_user,
    )
    self_eval_rc, self_eval, self_eval_stderr = _run_adapter(
        'Что со мной не так?',
        self_eval_user,
    )
    self_eval_followup_rc, self_eval_followup, self_eval_followup_stderr = _run_adapter(
        'скорее избегание',
        self_eval_user,
    )
    shame_rc, shame, shame_stderr = _run_adapter(
        'Мне стыдно за себя целиком',
        shame_user,
    )
    shame_followup_rc, shame_followup, shame_followup_stderr = _run_adapter(
        'скорее унижение',
        shame_user,
    )
    feedback_rc, feedback, feedback_stderr = _run_adapter(
        'ты задаёшь слишком много вопросов',
        feedback_user,
    )
    portrait_followup_rc, portrait_followup, portrait_followup_stderr = _run_adapter(
        'скорее избегание',
        portrait_user,
    )
    portrait_detail_rc, portrait_detail, portrait_detail_stderr = _run_adapter(
        'скорее разговор',
        portrait_user,
    )
    portrait_analysis_rc, portrait_analysis, portrait_analysis_stderr = _run_adapter(
        'и что это значит?',
        portrait_user,
    )
    portrait_next_step_rc, portrait_next_step, portrait_next_step_stderr = _run_adapter(
        'и что с этим делать?',
        portrait_user,
    )
    portrait_example_rc, portrait_example, portrait_example_stderr = _run_adapter(
        'приведи пример',
        portrait_user,
    )
    topic_shift_user = f'telegram:dialogue-shift-{uuid.uuid4().hex[:8]}'
    personalize_user = f'telegram:dialogue-personalize-{uuid.uuid4().hex[:8]}'
    shift_seed_rc, shift_seed, shift_seed_stderr = _run_adapter(
        'Какие могут быть причины потери чувств в серьезных отношениях?',
        topic_shift_user,
    )
    topic_shift_rc, topic_shift, topic_shift_stderr = _run_adapter(
        'ладно, другой вопрос: я подозреваю, что у меня ангедония',
        topic_shift_user,
    )
    personalize_seed_rc, personalize_seed, personalize_seed_stderr = _run_adapter(
        'Какие могут быть причины потери чувств в серьезных отношениях?',
        personalize_user,
    )
    personalize_general_rc, personalize_general, personalize_general_stderr = _run_adapter(
        'Я имею ввиду абстрактно, не конкретно у меня',
        personalize_user,
    )
    personalize_rc, personalize, personalize_stderr = _run_adapter(
        'а если у меня лично?',
        personalize_user,
    )
    cause_list_user = f'telegram:dialogue-causes-{uuid.uuid4().hex[:8]}'
    cause_seed_rc, cause_seed, cause_seed_stderr = _run_adapter(
        'Какие могут быть причины потери чувств в серьезных отношениях?',
        cause_list_user,
    )
    cause_general_rc, cause_general, cause_general_stderr = _run_adapter(
        'Я имею ввиду абстрактно, не конкретно у меня',
        cause_list_user,
    )
    cause_list_rc, cause_list_payload, cause_list_stderr = _run_adapter(
        'какие основные причины?',
        cause_list_user,
    )
    cause_next_step_rc, cause_next_step_payload, cause_next_step_stderr = _run_adapter(
        'и что с этим делать?',
        cause_list_user,
    )
    cause_example_rc, cause_example_payload, cause_example_stderr = _run_adapter(
        'приведи пример',
        cause_list_user,
    )
    reject_scope_user = f'telegram:dialogue-reject-{uuid.uuid4().hex[:8]}'
    reject_seed_rc, reject_seed, reject_seed_stderr = _run_adapter(
        'Какие могут быть причины потери чувств в серьезных отношениях?',
        reject_scope_user,
    )
    reject_general_rc, reject_general, reject_general_stderr = _run_adapter(
        'Я имею ввиду абстрактно, не конкретно у меня',
        reject_scope_user,
    )
    reject_scope_rc, reject_scope_payload, reject_scope_stderr = _run_adapter(
        'слишком общо',
        reject_scope_user,
    )

    portrait_meta = portrait.get('decision_metadata') or {}
    diagnosis_meta = diagnosis.get('decision_metadata') or {}
    diagnosis_followup_meta = diagnosis_followup.get('decision_metadata') or {}
    diagnosis_early_seed_meta = diagnosis_early_seed.get('decision_metadata') or {}
    diagnosis_early_followup_meta = diagnosis_early_followup.get('decision_metadata') or {}
    diagnosis_early_next_step_meta = diagnosis_early_next_step.get('decision_metadata') or {}
    diagnosis_detail_meta = diagnosis_detail.get('decision_metadata') or {}
    diagnosis_analysis_meta = diagnosis_analysis.get('decision_metadata') or {}
    diagnosis_next_step_meta = diagnosis_next_step.get('decision_metadata') or {}
    diagnosis_example_meta = diagnosis_example.get('decision_metadata') or {}
    menu_meta = menu.get('decision_metadata') or {}
    self_eval_meta = self_eval.get('decision_metadata') or {}
    self_eval_followup_meta = self_eval_followup.get('decision_metadata') or {}
    shame_meta = shame.get('decision_metadata') or {}
    shame_followup_meta = shame_followup.get('decision_metadata') or {}
    feedback_meta = feedback.get('decision_metadata') or {}
    portrait_followup_meta = portrait_followup.get('decision_metadata') or {}
    portrait_detail_meta = portrait_detail.get('decision_metadata') or {}
    portrait_analysis_meta = portrait_analysis.get('decision_metadata') or {}
    portrait_next_step_meta = portrait_next_step.get('decision_metadata') or {}
    portrait_example_meta = portrait_example.get('decision_metadata') or {}
    shift_seed_meta = shift_seed.get('decision_metadata') or {}
    topic_shift_meta = topic_shift.get('decision_metadata') or {}
    personalize_seed_meta = personalize_seed.get('decision_metadata') or {}
    personalize_general_meta = personalize_general.get('decision_metadata') or {}
    personalize_meta = personalize.get('decision_metadata') or {}
    cause_seed_meta = cause_seed.get('decision_metadata') or {}
    cause_general_meta = cause_general.get('decision_metadata') or {}
    cause_list_meta = cause_list_payload.get('decision_metadata') or {}
    cause_next_step_meta = cause_next_step_payload.get('decision_metadata') or {}
    cause_example_meta = cause_example_payload.get('decision_metadata') or {}
    reject_seed_meta = reject_seed.get('decision_metadata') or {}
    reject_general_meta = reject_general.get('decision_metadata') or {}
    reject_scope_meta = reject_scope_payload.get('decision_metadata') or {}

    results = [
        {
            'name': 'psychological_portrait_becomes_pattern_clarify',
            'pass': (
                portrait_rc == 0
                and portrait.get('reason_code') == 'psychological-portrait-request'
                and portrait_meta.get('dialogue_act') == 'request_psychological_portrait'
                and portrait_meta.get('active_topic') == 'psychological-portrait'
                and portrait_meta.get('pending_slot') == 'pattern_selection'
                and 'тип' in (portrait.get('final_user_text') or '').lower()
                and 'личност' in (portrait.get('final_user_text') or '').lower()
                and 'книг' not in (portrait.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'self_diagnosis_becomes_symptom_clarify',
            'pass': (
                diagnosis_rc == 0
                and diagnosis.get('reason_code') == 'self-diagnosis-soft'
                and diagnosis_meta.get('dialogue_act') == 'self_diagnosis_soft'
                and diagnosis_meta.get('active_topic') == 'self-diagnosis'
                and diagnosis_meta.get('pending_slot') == 'symptom_narrowing'
                and 'диагноз' in (diagnosis.get('final_user_text') or '').lower()
                and 'цитат' not in (diagnosis.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'self_diagnosis_followup_advances_to_axis_specific_clarify',
            'pass': (
                diagnosis_followup_rc == 0
                and diagnosis_followup.get('reason_code') == 'self-diagnosis-axis-followup'
                and diagnosis_followup_meta.get('dialogue_act') == 'supply_narrowing_axis'
                and diagnosis_followup_meta.get('active_topic') == 'self-diagnosis'
                and diagnosis_followup_meta.get('dialogue_mode') == 'followup_narrowing'
                and diagnosis_followup_meta.get('active_axis') == 'emotional_flatness'
                and diagnosis_followup_meta.get('selected_axis') == 'emotional_flatness'
                and 'если главнее пустота' in (diagnosis_followup.get('final_user_text') or '').lower()
                and 'цитат' not in (diagnosis_followup.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'self_diagnosis_early_next_step_keeps_frame_and_legacy_metadata_in_sync',
            'pass': (
                diagnosis_early_seed_rc == 0
                and diagnosis_early_seed_meta.get('active_topic') == 'self-diagnosis'
                and diagnosis_early_followup_rc == 0
                and diagnosis_early_followup_meta.get('active_topic') == 'self-diagnosis'
                and diagnosis_early_next_step_rc == 0
                and diagnosis_early_next_step.get('reason_code') == 'self-diagnosis-next-step'
                and diagnosis_early_next_step_meta.get('dialogue_act') == 'request_next_step'
                and diagnosis_early_next_step_meta.get('dialogue_mode') == 'practical_next_step'
                and diagnosis_early_next_step_meta.get('active_topic') == 'self-diagnosis'
                and diagnosis_early_next_step_meta.get('pending_slot') == 'example_or_shift'
                and diagnosis_early_next_step_meta.get('frame_topic') == 'self-diagnosis'
                and diagnosis_early_next_step_meta.get('frame_goal') == 'next_step'
            ),
        },
        {
            'name': 'self_evaluation_becomes_pattern_clarify',
            'pass': (
                self_eval_rc == 0
                and self_eval.get('reason_code') == 'self-evaluation-request'
                and self_eval_meta.get('active_topic') == 'self-evaluation'
                and self_eval_meta.get('pending_slot') == 'pattern_selection'
                and 'ярлык' in (self_eval.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'self_evaluation_followup_advances_to_pattern_specific_clarify',
            'pass': (
                self_eval_followup_rc == 0
                and self_eval_followup.get('reason_code') == 'self-evaluation-axis-followup'
                and self_eval_followup_meta.get('dialogue_act') == 'supply_narrowing_axis'
                and self_eval_followup_meta.get('active_topic') == 'self-evaluation'
                and self_eval_followup_meta.get('dialogue_mode') == 'followup_narrowing'
                and self_eval_followup_meta.get('active_axis') == 'avoidance'
            ),
        },
        {
            'name': 'shame_family_becomes_narrowing_clarify',
            'pass': (
                shame_rc == 0
                and shame.get('reason_code') == 'shame-self-contempt-request'
                and shame_meta.get('active_topic') == 'shame-self-contempt'
                and shame_meta.get('pending_slot') == 'narrowing_axis'
                and 'стыд' in (shame.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'shame_family_followup_advances_to_axis_specific_clarify',
            'pass': (
                shame_followup_rc == 0
                and shame_followup.get('reason_code') == 'shame-self-contempt-axis-followup'
                and shame_followup_meta.get('dialogue_act') == 'supply_narrowing_axis'
                and shame_followup_meta.get('active_topic') == 'shame-self-contempt'
                and shame_followup_meta.get('dialogue_mode') == 'followup_narrowing'
                and shame_followup_meta.get('active_axis') == 'humiliation'
            ),
        },
        {
            'name': 'conversation_feedback_becomes_meta_scope_instead_of_source_lookup',
            'pass': (
                feedback_rc == 0
                and feedback.get('reason_code') == 'conversation-feedback'
                and feedback_meta.get('dialogue_act') == 'request_conversation_feedback'
                and feedback_meta.get('active_topic') == 'conversation-feedback'
                and feedback_meta.get('dialogue_mode') == 'scope_clarify'
                and 'не будем превращать разговор в допрос' in (feedback.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'portrait_followup_advances_to_pattern_specific_clarify',
            'pass': (
                portrait_followup_rc == 0
                and portrait_followup.get('reason_code') == 'psychological-portrait-axis-followup'
                and portrait_followup_meta.get('dialogue_act') == 'supply_narrowing_axis'
                and portrait_followup_meta.get('active_topic') == 'psychological-portrait'
                and portrait_followup_meta.get('dialogue_mode') == 'followup_narrowing'
                and portrait_followup_meta.get('active_axis') == 'avoidance'
                and portrait_followup_meta.get('selected_axis') == 'avoidance'
                and 'вредишь себе через избегание' in (portrait_followup.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'self_diagnosis_detail_followup_deepens_same_thread',
            'pass': (
                diagnosis_detail_rc == 0
                and diagnosis_detail.get('reason_code') == 'self-diagnosis-detail-followup'
                and diagnosis_detail_meta.get('dialogue_act') == 'supply_concrete_manifestation'
                and diagnosis_detail_meta.get('active_topic') == 'self-diagnosis'
                and diagnosis_detail_meta.get('dialogue_mode') == 'followup_deepen'
                and diagnosis_detail_meta.get('active_axis') == 'emotional_flatness'
                and diagnosis_detail_meta.get('active_detail') == 'social_disconnection'
                and diagnosis_detail_meta.get('selected_detail') == 'social_disconnection'
                and 'выпадает из той связи' in (diagnosis_detail.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'portrait_detail_followup_deepens_same_thread',
            'pass': (
                portrait_detail_rc == 0
                and portrait_detail.get('reason_code') == 'psychological-portrait-detail-followup'
                and portrait_detail_meta.get('dialogue_act') == 'supply_concrete_manifestation'
                and portrait_detail_meta.get('active_topic') == 'psychological-portrait'
                and portrait_detail_meta.get('dialogue_mode') == 'followup_deepen'
                and portrait_detail_meta.get('active_axis') == 'avoidance'
                and portrait_detail_meta.get('active_detail') == 'conversation'
                and portrait_detail_meta.get('selected_detail') == 'conversation'
                and 'правда требует голоса' in (portrait_detail.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'self_diagnosis_mini_analysis_explains_pattern_after_detail',
            'pass': (
                diagnosis_analysis_rc == 0
                and diagnosis_analysis.get('reason_code') == 'self-diagnosis-mini-analysis'
                and diagnosis_analysis_meta.get('dialogue_act') == 'request_mini_analysis'
                and diagnosis_analysis_meta.get('dialogue_mode') == 'mini_analysis'
                and diagnosis_analysis_meta.get('active_topic') == 'self-diagnosis'
                and diagnosis_analysis_meta.get('active_axis') == 'emotional_flatness'
                and diagnosis_analysis_meta.get('active_detail') == 'social_disconnection'
                and diagnosis_analysis_meta.get('response_move') == 'acknowledge_and_continue'
                and (
                    'если держаться именно этого узла' in (
                        diagnosis_analysis.get('final_user_text') or ''
                    ).lower()
                    or 'понять её внутреннюю механику' in (
                        diagnosis_analysis.get('final_user_text') or ''
                    ).lower()
                )
                and 'выпадает из живой взаимности' in (diagnosis_analysis.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'portrait_mini_analysis_explains_pattern_after_detail',
            'pass': (
                portrait_analysis_rc == 0
                and portrait_analysis.get('reason_code') == 'psychological-portrait-mini-analysis'
                and portrait_analysis_meta.get('dialogue_act') == 'request_mini_analysis'
                and portrait_analysis_meta.get('dialogue_mode') == 'mini_analysis'
                and portrait_analysis_meta.get('active_topic') == 'psychological-portrait'
                and portrait_analysis_meta.get('active_axis') == 'avoidance'
                and portrait_analysis_meta.get('active_detail') == 'conversation'
                and portrait_analysis_meta.get('response_move') == 'acknowledge_and_continue'
                and 'если держаться именно этого узла' in (
                    portrait_analysis.get('final_user_text') or ''
                ).lower()
                and 'молчание здесь становится способом отложить реальность' in (portrait_analysis.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'self_diagnosis_next_step_turns_analysis_into_practical_guidance',
            'pass': (
                diagnosis_next_step_rc == 0
                and diagnosis_next_step.get('reason_code') == 'self-diagnosis-next-step'
                and diagnosis_next_step_meta.get('dialogue_act') == 'request_next_step'
                and diagnosis_next_step_meta.get('dialogue_mode') == 'practical_next_step'
                and diagnosis_next_step_meta.get('active_topic') == 'self-diagnosis'
                and diagnosis_next_step_meta.get('active_axis') == 'emotional_flatness'
                and diagnosis_next_step_meta.get('active_detail') == 'social_disconnection'
                and diagnosis_next_step_meta.get('response_move') == 'acknowledge_and_continue'
                and (
                    'не будем снова расширять тему' in (
                        diagnosis_next_step.get('final_user_text') or ''
                    ).lower()
                    or 'пора не расширять тему, а перевести её в действие' in (
                        diagnosis_next_step.get('final_user_text') or ''
                    ).lower()
                )
                and 'один настоящий контакт' in (diagnosis_next_step.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'portrait_next_step_turns_analysis_into_practical_guidance',
            'pass': (
                portrait_next_step_rc == 0
                and portrait_next_step.get('reason_code') == 'psychological-portrait-next-step'
                and portrait_next_step_meta.get('dialogue_act') == 'request_next_step'
                and portrait_next_step_meta.get('dialogue_mode') == 'practical_next_step'
                and portrait_next_step_meta.get('active_topic') == 'psychological-portrait'
                and portrait_next_step_meta.get('active_axis') == 'avoidance'
                and portrait_next_step_meta.get('active_detail') == 'conversation'
                and portrait_next_step_meta.get('response_move') == 'acknowledge_and_continue'
                and (
                    'не будем снова расширять тему' in (
                        portrait_next_step.get('final_user_text') or ''
                    ).lower()
                    or 'переведём это в один честный следующий шаг' in (
                        portrait_next_step.get('final_user_text') or ''
                    ).lower()
                    or 'пора не расширять тему, а перевести её в действие' in (
                        portrait_next_step.get('final_user_text') or ''
                    ).lower()
                )
                and 'один разговор' in (portrait_next_step.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'self_diagnosis_example_turns_thread_into_illustration',
            'pass': (
                diagnosis_example_rc == 0
                and diagnosis_example.get('reason_code') == 'self-diagnosis-example'
                and diagnosis_example_meta.get('dialogue_act') == 'request_example'
                and diagnosis_example_meta.get('dialogue_mode') == 'example_illustration'
                and diagnosis_example_meta.get('active_topic') == 'self-diagnosis'
                and diagnosis_example_meta.get('active_axis') == 'emotional_flatness'
                and diagnosis_example_meta.get('active_detail') == 'social_disconnection'
                and diagnosis_example_meta.get('response_move') == 'acknowledge_and_continue'
                and 'не останемся на уровне схемы' in (diagnosis_example.get('final_user_text') or '').lower()
                and 'вежливо' in (diagnosis_example.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'portrait_example_turns_thread_into_illustration',
            'pass': (
                portrait_example_rc == 0
                and portrait_example.get('reason_code') == 'psychological-portrait-example'
                and portrait_example_meta.get('dialogue_act') == 'request_example'
                and portrait_example_meta.get('dialogue_mode') == 'example_illustration'
                and portrait_example_meta.get('active_topic') == 'psychological-portrait'
                and portrait_example_meta.get('active_axis') == 'avoidance'
                and portrait_example_meta.get('active_detail') == 'conversation'
                and portrait_example_meta.get('response_move') == 'acknowledge_and_continue'
                and (
                    'не останемся на уровне схемы' in (portrait_example.get('final_user_text') or '').lower()
                    or 'посмотрим, как этот узел выглядит в живом примере' in (portrait_example.get('final_user_text') or '').lower()
                )
                and 'откладывает разговор' in (portrait_example.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'menu_request_uses_scope_mode',
            'pass': (
                menu_rc == 0
                and menu.get('reason_code') == 'scope-topics'
                and menu_meta.get('dialogue_act') == 'request_menu'
                and menu_meta.get('active_topic') == 'scope-topics'
                and menu_meta.get('dialogue_mode') == 'scope_clarify'
                and menu_meta.get('pending_slot') == 'topic_selection'
            ),
        },
        {
            'name': 'topic_shift_opens_new_human_problem_thread_without_mixing_topics',
            'pass': (
                shift_seed_rc == 0
                and shift_seed_meta.get('active_topic') == 'relationship-loss-of-feeling'
                and topic_shift_rc == 0
                and topic_shift.get('reason_code') == 'self-diagnosis-soft'
                and topic_shift_meta.get('dialogue_act') == 'topic_shift'
                and topic_shift_meta.get('active_topic') == 'self-diagnosis'
                and topic_shift_meta.get('dialogue_mode') == 'human_problem_clarify'
                and topic_shift_meta.get('pending_slot') == 'symptom_narrowing'
                and topic_shift_meta.get('topic_reused') is False
                and topic_shift_meta.get('response_move') == 'acknowledge_and_continue'
                and 'оставим прежний узел' in (topic_shift.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'personalize_previous_question_returns_general_thread_back_to_personal',
            'pass': (
                personalize_seed_rc == 0
                and personalize_seed_meta.get('active_topic') == 'relationship-loss-of-feeling'
                and personalize_general_rc == 0
                and personalize_general_meta.get('abstraction_level') == 'general'
                and personalize_rc == 0
                and personalize.get('reason_code') == 'relationship-knot'
                and personalize_meta.get('dialogue_act') == 'personalize_previous_question'
                and personalize_meta.get('active_topic') == 'relationship-loss-of-feeling'
                and personalize_meta.get('abstraction_level') == 'personal'
                and personalize_meta.get('dialogue_mode') == 'human_problem_clarify'
                and personalize_meta.get('pending_slot') == 'narrowing_axis'
                and personalize_meta.get('topic_reused') is True
                and personalize_meta.get('response_move') == 'acknowledge_and_continue'
                and 'вернём разговор от общей схемы к тебе лично' in (personalize.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'request_cause_list_lists_main_causes_inside_same_general_thread',
            'pass': (
                cause_seed_rc == 0
                and cause_seed_meta.get('active_topic') == 'relationship-loss-of-feeling'
                and cause_general_rc == 0
                and cause_general_meta.get('abstraction_level') == 'general'
                and cause_list_rc == 0
                and cause_list_payload.get('reason_code') == 'relationship-loss-of-feeling-cause-list'
                and cause_list_meta.get('dialogue_act') == 'request_cause_list'
                and cause_list_meta.get('active_topic') == 'relationship-loss-of-feeling'
                and cause_list_meta.get('abstraction_level') == 'general'
                and cause_list_meta.get('dialogue_mode') == 'cause_list'
                and cause_list_meta.get('pending_slot') == 'narrowing_axis'
                and cause_list_meta.get('topic_reused') is True
                and cause_list_meta.get('response_move') == 'acknowledge_and_continue'
                and (
                    'разложим тему по главным причинам' in (cause_list_payload.get('final_user_text') or '').lower()
                    or 'тогда разложим тему по главным причинам' in (cause_list_payload.get('final_user_text') or '').lower()
                    or 'разложим по главным причинам' in (cause_list_payload.get('final_user_text') or '').lower()
                    or 'разложить тему по главным линиям' in (cause_list_payload.get('final_user_text') or '').lower()
                )
                and 'накопленная обида' in (cause_list_payload.get('final_user_text') or '').lower()
                and 'невысказанный конфликт' in (cause_list_payload.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'request_next_step_after_cause_list_keeps_same_general_thread_and_turns_practical',
            'pass': (
                cause_list_rc == 0
                and cause_list_meta.get('dialogue_mode') == 'cause_list'
                and cause_next_step_rc == 0
                and cause_next_step_payload.get('reason_code') == 'relationship-loss-of-feeling-next-step'
                and cause_next_step_meta.get('dialogue_act') == 'request_next_step'
                and cause_next_step_meta.get('dialogue_mode') == 'practical_next_step'
                and cause_next_step_meta.get('active_topic') == 'relationship-loss-of-feeling'
                and cause_next_step_meta.get('abstraction_level') == 'general'
                and cause_next_step_meta.get('topic_reused') is True
                and cause_next_step_meta.get('response_move') == 'acknowledge_and_continue'
                and (
                    'не будем снова расширять тему' in (cause_next_step_payload.get('final_user_text') or '').lower()
                    or 'переведём это в один честный следующий шаг' in (cause_next_step_payload.get('final_user_text') or '').lower()
                    or 'пора не расширять тему, а перевести её в действие' in (cause_next_step_payload.get('final_user_text') or '').lower()
                )
                and 'выбрать одну причину' in (cause_next_step_payload.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'request_example_after_cause_list_keeps_same_general_thread_and_illustrates_one_pattern',
            'pass': (
                cause_next_step_rc == 0
                and cause_next_step_meta.get('dialogue_mode') == 'practical_next_step'
                and cause_example_rc == 0
                and cause_example_payload.get('reason_code') == 'relationship-loss-of-feeling-example'
                and cause_example_meta.get('dialogue_act') == 'request_example'
                and cause_example_meta.get('dialogue_mode') == 'example_illustration'
                and cause_example_meta.get('active_topic') == 'relationship-loss-of-feeling'
                and cause_example_meta.get('abstraction_level') == 'general'
                and cause_example_meta.get('topic_reused') is True
                and cause_example_meta.get('response_move') == 'acknowledge_and_continue'
                and (
                    'не останемся на уровне схемы' in (cause_example_payload.get('final_user_text') or '').lower()
                    or 'посмотрим, как этот узел выглядит в живом примере' in (cause_example_payload.get('final_user_text') or '').lower()
                )
                and 'откладывается “до более спокойного момента”' in (cause_example_payload.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'reject_scope_uses_repair_wrong_level_instead_of_falling_back_to_source_lookup',
            'pass': (
                reject_seed_rc == 0
                and reject_seed_meta.get('active_topic') == 'relationship-loss-of-feeling'
                and reject_general_rc == 0
                and reject_general_meta.get('abstraction_level') == 'general'
                and reject_scope_rc == 0
                and reject_scope_payload.get('reason_code') == 'repair-wrong-level'
                and reject_scope_meta.get('active_topic') == 'repair-wrong-level'
                and reject_scope_meta.get('abstraction_level') == 'personal'
                and reject_scope_meta.get('dialogue_mode') == 'topic_opening'
                and reject_scope_meta.get('pending_slot') == 'narrowing_axis'
                and reject_scope_meta.get('marginal_router_status') == 'heuristic_fallback'
                and reject_scope_meta.get('marginal_router_result_route') == 'repair_wrong_level'
                and reject_scope_meta.get('topic_reused') is False
                and 'уберём общую рамку' in (reject_scope_payload.get('final_user_text') or '').lower()
            ),
        },
    ]

    emit_report(
        results,
        samples={
            'portrait': portrait,
            'self_diagnosis': diagnosis,
            'self_diagnosis_followup': diagnosis_followup,
            'self_diagnosis_early_seed': diagnosis_early_seed,
            'self_diagnosis_early_followup': diagnosis_early_followup,
            'self_diagnosis_early_next_step': diagnosis_early_next_step,
            'self_diagnosis_detail': diagnosis_detail,
            'self_diagnosis_analysis': diagnosis_analysis,
            'self_diagnosis_next_step': diagnosis_next_step,
            'self_diagnosis_example': diagnosis_example,
            'menu': menu,
            'self_evaluation': self_eval,
            'self_evaluation_followup': self_eval_followup,
            'shame': shame,
            'shame_followup': shame_followup,
            'feedback': feedback,
            'portrait_followup': portrait_followup,
            'portrait_detail': portrait_detail,
            'portrait_analysis': portrait_analysis,
            'portrait_next_step': portrait_next_step,
            'portrait_example': portrait_example,
            'topic_shift_seed': shift_seed,
            'topic_shift': topic_shift,
            'personalize_seed': personalize_seed,
            'personalize_general': personalize_general,
            'personalize': personalize,
            'cause_seed': cause_seed,
            'cause_general': cause_general,
            'cause_list': cause_list_payload,
            'cause_next_step': cause_next_step_payload,
            'cause_example': cause_example_payload,
            'reject_seed': reject_seed,
            'reject_general': reject_general,
            'reject_scope': reject_scope_payload,
        },
        stderr={
            'portrait': portrait_stderr,
            'self_diagnosis': diagnosis_stderr,
            'self_diagnosis_followup': diagnosis_followup_stderr,
            'self_diagnosis_early_seed': diagnosis_early_seed_stderr,
            'self_diagnosis_early_followup': diagnosis_early_followup_stderr,
            'self_diagnosis_early_next_step': diagnosis_early_next_step_stderr,
            'self_diagnosis_detail': diagnosis_detail_stderr,
            'self_diagnosis_analysis': diagnosis_analysis_stderr,
            'self_diagnosis_next_step': diagnosis_next_step_stderr,
            'self_diagnosis_example': diagnosis_example_stderr,
            'menu': menu_stderr,
            'self_evaluation': self_eval_stderr,
            'self_evaluation_followup': self_eval_followup_stderr,
            'shame': shame_stderr,
            'shame_followup': shame_followup_stderr,
            'feedback': feedback_stderr,
            'portrait_followup': portrait_followup_stderr,
            'portrait_detail': portrait_detail_stderr,
            'portrait_analysis': portrait_analysis_stderr,
            'portrait_next_step': portrait_next_step_stderr,
            'portrait_example': portrait_example_stderr,
            'topic_shift_seed': shift_seed_stderr,
            'topic_shift': topic_shift_stderr,
            'personalize_seed': personalize_seed_stderr,
            'personalize_general': personalize_general_stderr,
            'personalize': personalize_stderr,
            'cause_seed': cause_seed_stderr,
            'cause_general': cause_general_stderr,
            'cause_list': cause_list_stderr,
            'cause_next_step': cause_next_step_stderr,
            'cause_example': cause_example_stderr,
            'reject_seed': reject_seed_stderr,
            'reject_general': reject_general_stderr,
            'reject_scope': reject_scope_stderr,
        },
    )


if __name__ == '__main__':
    main()
