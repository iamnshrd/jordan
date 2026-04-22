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
    greeting_user = f'telegram:dialogue-greeting-{uuid.uuid4().hex[:8]}'
    menu_user = f'telegram:dialogue-menu2-{uuid.uuid4().hex[:8]}'
    portrait_user = f'telegram:dialogue-portrait2-{uuid.uuid4().hex[:8]}'
    implicit_shift_user = f'telegram:dialogue-shift2-{uuid.uuid4().hex[:8]}'

    greeting_rc, greeting, greeting_stderr = _run_adapter(
        'Добрый вечер, доктор Питерсон',
        greeting_user,
    )
    menu_rc, menu, menu_stderr = _run_adapter(
        'О чем с тобой можно поговорить?',
        menu_user,
    )

    portrait_seed_rc, portrait_seed, portrait_seed_stderr = _run_adapter(
        'Давайте составим мой психологический портрет',
        portrait_user,
    )
    portrait_general_rc, portrait_general, portrait_general_stderr = _run_adapter(
        'какие основные причины?',
        portrait_user,
    )
    portrait_personal_rc, portrait_personal, portrait_personal_stderr = _run_adapter(
        'а если у меня лично?',
        portrait_user,
    )

    shift_seed_rc, shift_seed, shift_seed_stderr = _run_adapter(
        'Давайте составим мой психологический портрет',
        implicit_shift_user,
    )
    shift_followup_rc, shift_followup, shift_followup_stderr = _run_adapter(
        'скорее избегание',
        implicit_shift_user,
    )
    implicit_shift_rc, implicit_shift, implicit_shift_stderr = _run_adapter(
        'Какие могут быть причины потери чувств в серьезных отношениях?',
        implicit_shift_user,
    )

    greeting_meta = greeting.get('decision_metadata') or {}
    menu_meta = menu.get('decision_metadata') or {}
    portrait_seed_meta = portrait_seed.get('decision_metadata') or {}
    portrait_general_meta = portrait_general.get('decision_metadata') or {}
    portrait_personal_meta = portrait_personal.get('decision_metadata') or {}
    shift_seed_meta = shift_seed.get('decision_metadata') or {}
    shift_followup_meta = shift_followup.get('decision_metadata') or {}
    implicit_shift_meta = implicit_shift.get('decision_metadata') or {}

    results = [
        {
            'name': 'greeting_does_not_fall_back_to_source_lookup',
            'pass': (
                greeting_rc == 0
                and greeting.get('reason_code') == 'greeting-opening'
                and greeting_meta.get('dialogue_act') == 'greeting_opening'
                and greeting_meta.get('active_topic') == 'greeting'
                and 'вежливость' in (greeting.get('final_user_text') or '').lower()
                and 'цитат' not in (greeting.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'menu_variant_with_s_toboy_hits_scope_topics',
            'pass': (
                menu_rc == 0
                and menu.get('reason_code') == 'scope-topics'
                and menu_meta.get('dialogue_act') == 'request_menu'
                and menu_meta.get('active_topic') == 'scope-topics'
                and menu_meta.get('pending_slot') == 'topic_selection'
                and 'смысл и направление' in (menu.get('final_user_text') or '').lower()
            ),
        },
        {
            'name': 'portrait_personalize_does_not_fall_back_to_source_lookup',
            'pass': (
                portrait_seed_rc == 0
                and portrait_general_rc == 0
                and portrait_personal_rc == 0
                and portrait_seed.get('reason_code') == 'psychological-portrait-request'
                and portrait_general.get('reason_code') == 'psychological-portrait-cause-list'
                and portrait_personal.get('reason_code') == 'psychological-portrait-request'
                and portrait_personal_meta.get('dialogue_act') == 'personalize_previous_question'
                and portrait_personal_meta.get('active_topic') == 'psychological-portrait'
                and portrait_personal_meta.get('abstraction_level') == 'personal'
                and portrait_personal_meta.get('topic_reused') is True
                and 'вернёмся от общей схемы характера к тебе лично' in (
                    portrait_personal.get('final_user_text') or ''
                ).lower()
            ),
        },
        {
            'name': 'fresh_relationship_question_does_not_get_trapped_in_old_pending_slot',
            'pass': (
                shift_seed_rc == 0
                and shift_followup_rc == 0
                and implicit_shift_rc == 0
                and shift_seed.get('reason_code') == 'psychological-portrait-request'
                and shift_followup.get('reason_code') == 'psychological-portrait-axis-followup'
                and implicit_shift.get('reason_code') == 'relationship-knot'
                and implicit_shift_meta.get('dialogue_act') == 'open_topic'
                and implicit_shift_meta.get('active_topic') == 'relationship-loss-of-feeling'
                and implicit_shift_meta.get('topic_reused') is False
                and implicit_shift_meta.get('active_axis') == ''
            ),
        },
    ]

    emit_report(
        results,
        samples={
            'greeting': greeting,
            'menu': menu,
            'portrait_seed': portrait_seed,
            'portrait_general': portrait_general,
            'portrait_personalize': portrait_personal,
            'shift_seed': shift_seed,
            'shift_followup': shift_followup,
            'implicit_shift': implicit_shift,
        },
        stderr={
            'greeting': greeting_stderr,
            'menu': menu_stderr,
            'portrait_seed': portrait_seed_stderr,
            'portrait_general': portrait_general_stderr,
            'portrait_personalize': portrait_personal_stderr,
            'shift_seed': shift_seed_stderr,
            'shift_followup': shift_followup_stderr,
            'implicit_shift': implicit_shift_stderr,
        },
    )


if __name__ == '__main__':
    main()
