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
    user_id = f'telegram:dialogue-frame-{uuid.uuid4().hex[:8]}'
    seed_rc, seed, seed_stderr = _run_adapter(
        'Какие могут быть причины потери чувств в серьезных отношениях?',
        user_id,
    )
    follow_rc, follow, follow_stderr = _run_adapter(
        'Я имею ввиду абстрактно, не конкретно у меня',
        user_id,
    )
    foundations_rc, foundations, foundations_stderr = _run_adapter(
        'В чем заключается смысл крепких отношений?',
        f'{user_id}-foundations',
    )
    lost_rc, lost, lost_stderr = _run_adapter(
        'я потерял смысл и направление',
        f'{user_id}-lost',
    )
    foundations_variant_rc, foundations_variant, foundations_variant_stderr = _run_adapter(
        'Что делает отношения крепкими?',
        f'{user_id}-foundations-variant',
    )
    marriage_variant_rc, marriage_variant, marriage_variant_stderr = _run_adapter(
        'На чем держится брак?',
        f'{user_id}-marriage-foundations',
    )
    menu_variant_rc, menu_variant, menu_variant_stderr = _run_adapter(
        'На какие темы с тобой можно говорить?',
        f'{user_id}-scope-menu',
    )
    menu_variant_two_rc, menu_variant_two, menu_variant_two_stderr = _run_adapter(
        'Что мы можем обсудить?',
        f'{user_id}-scope-menu-two',
    )
    self_eval_rc, self_eval, self_eval_stderr = _run_adapter(
        'Что со мной не так?',
        f'{user_id}-self-eval',
    )
    self_eval_variant_rc, self_eval_variant, self_eval_variant_stderr = _run_adapter(
        'Почему я всё порчу?',
        f'{user_id}-self-eval-variant',
    )
    shame_rc, shame, shame_stderr = _run_adapter(
        'Мне стыдно за себя целиком',
        f'{user_id}-shame',
    )
    shame_variant_rc, shame_variant, shame_variant_stderr = _run_adapter(
        'Я себя ненавижу',
        f'{user_id}-shame-variant',
    )
    foundations_semantic_rc, foundations_semantic, foundations_semantic_stderr = _run_adapter(
        'Из чего строится по-настоящему крепкий брак?',
        f'{user_id}-foundations-semantic',
    )
    lost_semantic_rc, lost_semantic, lost_semantic_stderr = _run_adapter(
        'Я вообще не понимаю, ради чего двигаться дальше по жизни',
        f'{user_id}-lost-semantic',
    )
    self_eval_semantic_rc, self_eval_semantic, self_eval_semantic_stderr = _run_adapter(
        'Почему я сам себе всё ломаю?',
        f'{user_id}-self-eval-semantic',
    )
    shame_semantic_rc, shame_semantic, shame_semantic_stderr = _run_adapter(
        'Мне омерзительно смотреть на себя',
        f'{user_id}-shame-semantic',
    )
    greeting_rc, greeting, greeting_stderr = _run_adapter(
        'Добрый вечер, доктор Питерсон',
        f'{user_id}-greeting',
    )
    small_talk_rc, small_talk, small_talk_stderr = _run_adapter(
        'Как ваши дела?',
        f'{user_id}-small-talk',
    )
    address_rc, address, address_stderr = _run_adapter(
        'Доктор Питерсон, как к вам обращаться?',
        f'{user_id}-address',
    )
    sharing_rc, sharing, sharing_stderr = _run_adapter(
        'У меня есть некоторые проблемы, я хочу поделиться',
        f'{user_id}-sharing',
    )
    life_direction_rc, life_direction, life_direction_stderr = _run_adapter(
        'Как мне дальше жить',
        f'{user_id}-life-direction',
    )
    slang_greeting_rc, slang_greeting, slang_greeting_stderr = _run_adapter(
        'Здарова',
        f'{user_id}-slang-greeting',
    )
    renderer_check_rc, renderer_check, renderer_check_stderr = _run_adapter(
        'Проверяем рендерер',
        f'{user_id}-renderer-check',
    )
    appearance_rc, appearance, appearance_stderr = _run_adapter(
        'Как стать красивым',
        f'{user_id}-appearance',
    )

    seed_meta = seed.get('decision_metadata') or {}
    follow_meta = follow.get('decision_metadata') or {}
    foundations_meta = foundations.get('decision_metadata') or {}
    lost_meta = lost.get('decision_metadata') or {}
    foundations_variant_meta = foundations_variant.get('decision_metadata') or {}
    marriage_variant_meta = marriage_variant.get('decision_metadata') or {}
    menu_variant_meta = menu_variant.get('decision_metadata') or {}
    menu_variant_two_meta = menu_variant_two.get('decision_metadata') or {}
    self_eval_meta = self_eval.get('decision_metadata') or {}
    self_eval_variant_meta = self_eval_variant.get('decision_metadata') or {}
    shame_meta = shame.get('decision_metadata') or {}
    shame_variant_meta = shame_variant.get('decision_metadata') or {}
    foundations_semantic_meta = foundations_semantic.get('decision_metadata') or {}
    lost_semantic_meta = lost_semantic.get('decision_metadata') or {}
    self_eval_semantic_meta = self_eval_semantic.get('decision_metadata') or {}
    shame_semantic_meta = shame_semantic.get('decision_metadata') or {}
    greeting_meta = greeting.get('decision_metadata') or {}
    small_talk_meta = small_talk.get('decision_metadata') or {}
    address_meta = address.get('decision_metadata') or {}
    sharing_meta = sharing.get('decision_metadata') or {}
    life_direction_meta = life_direction.get('decision_metadata') or {}
    slang_greeting_meta = slang_greeting.get('decision_metadata') or {}
    renderer_check_meta = renderer_check.get('decision_metadata') or {}
    appearance_meta = appearance.get('decision_metadata') or {}
    seed_frame = seed.get('dialogue_frame') or {}
    follow_frame = follow.get('dialogue_frame') or {}
    foundations_frame = foundations.get('dialogue_frame') or {}
    lost_frame = lost.get('dialogue_frame') or {}
    foundations_variant_frame = foundations_variant.get('dialogue_frame') or {}
    marriage_variant_frame = marriage_variant.get('dialogue_frame') or {}
    menu_variant_frame = menu_variant.get('dialogue_frame') or {}
    menu_variant_two_frame = menu_variant_two.get('dialogue_frame') or {}
    self_eval_frame = self_eval.get('dialogue_frame') or {}
    self_eval_variant_frame = self_eval_variant.get('dialogue_frame') or {}
    shame_frame = shame.get('dialogue_frame') or {}
    shame_variant_frame = shame_variant.get('dialogue_frame') or {}
    foundations_semantic_frame = foundations_semantic.get('dialogue_frame') or {}
    lost_semantic_frame = lost_semantic.get('dialogue_frame') or {}
    self_eval_semantic_frame = self_eval_semantic.get('dialogue_frame') or {}
    shame_semantic_frame = shame_semantic.get('dialogue_frame') or {}
    greeting_frame = greeting.get('dialogue_frame') or {}
    small_talk_frame = small_talk.get('dialogue_frame') or {}
    address_frame = address.get('dialogue_frame') or {}
    sharing_frame = sharing.get('dialogue_frame') or {}
    life_direction_frame = life_direction.get('dialogue_frame') or {}
    slang_greeting_frame = slang_greeting.get('dialogue_frame') or {}
    renderer_check_frame = renderer_check.get('dialogue_frame') or {}
    appearance_frame = appearance.get('dialogue_frame') or {}

    results = [
        {
            'name': 'adapter_result_includes_dialogue_frame',
            'pass': (
                seed_rc == 0
                and seed_frame.get('topic') == 'relationship-loss-of-feeling'
                and seed_meta.get('frame_topic') == 'relationship-loss-of-feeling'
                and seed_meta.get('frame_type') == 'relationship_problem'
                and seed_meta.get('frame_goal') == 'clarify'
                and seed_frame.get('goal') == 'clarify'
                and seed_meta.get('frame_pending_slot') == 'narrowing_axis'
            ),
        },
        {
            'name': 'followup_updates_frame_stance_and_relation',
            'pass': (
                follow_rc == 0
                and follow_meta.get('dialogue_act') == 'abstractify_previous_question'
                and follow_meta.get('frame_topic') == 'relationship-loss-of-feeling'
                and follow_meta.get('frame_stance') == 'general'
                and follow_meta.get('frame_goal') == 'overview'
                and follow_meta.get('frame_relation_to_previous') == 'reframe'
                and follow_frame.get('topic') == 'relationship-loss-of-feeling'
                and follow_frame.get('stance') == 'general'
                and follow_frame.get('goal') == 'overview'
            ),
        },
        {
            'name': 'greeting_question_uses_registry_backed_greeting_frame',
            'pass': (
                greeting_rc == 0
                and greeting_meta.get('frame_topic') == 'greeting'
                and greeting_meta.get('frame_goal') == 'opening'
                and greeting_meta.get('frame_type') == 'greeting'
                and greeting_meta.get('frame_update_source') in {'family_registry', 'control_command'}
                and greeting_meta.get('clarify_reason_code') == 'greeting-opening'
                and greeting_frame.get('topic') == 'greeting'
                and greeting_frame.get('goal') == 'opening'
            ),
        },
        {
            'name': 'conversational_openings_use_controlled_frames',
            'pass': (
                small_talk_rc == 0
                and address_rc == 0
                and sharing_rc == 0
                and life_direction_rc == 0
                and small_talk_meta.get('frame_topic') == 'social-small-talk'
                and small_talk_meta.get('clarify_reason_code') == 'social-small-talk'
                and small_talk_frame.get('topic') == 'social-small-talk'
                and address_meta.get('frame_topic') == 'how-to-address'
                and address_meta.get('clarify_reason_code') == 'how-to-address'
                and address_frame.get('topic') == 'how-to-address'
                and sharing_meta.get('frame_topic') == 'problem-sharing-opening'
                and sharing_meta.get('clarify_reason_code') == 'problem-sharing-opening'
                and sharing_frame.get('topic') == 'problem-sharing-opening'
                and life_direction_meta.get('frame_topic') == 'life-direction-opening'
                and life_direction_meta.get('clarify_reason_code') == 'life-direction-opening'
                and life_direction_frame.get('topic') == 'life-direction-opening'
            ),
        },
        {
            'name': 'remaining_opening_edge_cases_use_controlled_frames',
            'pass': (
                slang_greeting_rc == 0
                and renderer_check_rc == 0
                and appearance_rc == 0
                and slang_greeting_meta.get('frame_topic') == 'greeting'
                and slang_greeting_meta.get('clarify_reason_code') == 'greeting-opening'
                and slang_greeting_frame.get('topic') == 'greeting'
                and renderer_check_meta.get('frame_topic') == 'social-small-talk'
                and renderer_check_meta.get('clarify_reason_code') == 'social-small-talk'
                and renderer_check_frame.get('topic') == 'social-small-talk'
                and appearance_meta.get('frame_topic') == 'appearance-self-presentation'
                and appearance_meta.get('clarify_reason_code') == 'appearance-self-presentation'
                and appearance_frame.get('topic') == 'appearance-self-presentation'
            ),
        },
        {
            'name': 'relationship_foundations_question_uses_foundations_frame',
            'pass': (
                foundations_rc == 0
                and foundations_meta.get('frame_topic') == 'relationship-foundations'
                and foundations_meta.get('frame_goal') == 'overview'
                and foundations_frame.get('topic') == 'relationship-foundations'
                and foundations_frame.get('stance') == 'general'
                and (
                    foundations_meta.get('clarify_reason_code') == 'relationship-foundations-overview'
                    or foundations.get('reason_code') == 'respond-with-kb'
                )
            ),
        },
        {
            'name': 'lost_and_aimless_question_uses_controlled_frame',
            'pass': (
                lost_rc == 0
                and lost.get('decision_type') == 'clarify'
                and lost.get('delivery_mode') == 'final_text'
                and lost.get('allow_model_call') is False
                and lost_meta.get('frame_topic') == 'lost-and-aimless'
                and lost_meta.get('frame_type') == 'meaning_direction'
                and lost_meta.get('frame_goal') == 'clarify'
                and lost_meta.get('clarify_reason_code') == 'lost-and-aimless'
                and lost_frame.get('topic') == 'lost-and-aimless'
                and lost_frame.get('frame_type') == 'meaning_direction'
            ),
        },
        {
            'name': 'relationship_foundations_variants_use_same_frame_family',
            'pass': (
                foundations_variant_rc == 0
                and marriage_variant_rc == 0
                and foundations_variant_meta.get('frame_topic') in {'relationship-foundations', 'relationship-opening-broad'}
                and foundations_variant_meta.get('frame_goal') in {'overview', 'opening'}
                and foundations_variant_frame.get('topic') in {'relationship-foundations', 'relationship-opening-broad'}
                and marriage_variant_meta.get('frame_topic') in {'relationship-foundations', 'relationship-opening-broad'}
                and marriage_variant_meta.get('frame_goal') in {'overview', 'opening'}
                and marriage_variant_frame.get('topic') in {'relationship-foundations', 'relationship-opening-broad'}
                and (
                    foundations_variant_meta.get('clarify_reason_code') == 'relationship-foundations-overview'
                    or foundations_variant_meta.get('clarify_reason_code') == 'relationship-opening-broad'
                    or foundations_variant.get('reason_code') == 'respond-with-kb'
                )
                and (
                    marriage_variant_meta.get('clarify_reason_code') == 'relationship-foundations-overview'
                    or marriage_variant_meta.get('clarify_reason_code') == 'relationship-opening-broad'
                    or marriage_variant.get('reason_code') == 'respond-with-kb'
                )
            ),
        },
        {
            'name': 'scope_menu_variants_use_same_frame_family',
            'pass': (
                menu_variant_rc == 0
                and menu_variant_two_rc == 0
                and menu_variant.get('decision_type') == 'clarify'
                and menu_variant.get('delivery_mode') == 'final_text'
                and menu_variant.get('allow_model_call') is False
                and menu_variant_meta.get('frame_topic') == 'scope-topics'
                and menu_variant_meta.get('frame_goal') == 'menu'
                and menu_variant_meta.get('frame_type') == 'scope_menu'
                and menu_variant_meta.get('clarify_reason_code') == 'scope-topics'
                and menu_variant_frame.get('topic') == 'scope-topics'
                and menu_variant_two_meta.get('frame_topic') == 'scope-topics'
                and menu_variant_two_meta.get('frame_goal') == 'menu'
                and menu_variant_two_meta.get('frame_type') == 'scope_menu'
                and menu_variant_two_meta.get('clarify_reason_code') == 'scope-topics'
                and menu_variant_two_frame.get('topic') == 'scope-topics'
            ),
        },
        {
            'name': 'self_evaluation_variants_use_same_frame_family',
            'pass': (
                self_eval_rc == 0
                and self_eval_variant_rc == 0
                and self_eval.get('decision_type') == 'clarify'
                and self_eval.get('delivery_mode') == 'final_text'
                and self_eval.get('allow_model_call') is False
                and self_eval_meta.get('frame_topic') == 'self-evaluation'
                and self_eval_meta.get('frame_goal') == 'clarify'
                and self_eval_meta.get('frame_type') == 'self_inquiry'
                and self_eval_meta.get('clarify_reason_code') == 'self-evaluation-request'
                and self_eval_frame.get('topic') == 'self-evaluation'
                and self_eval_variant_meta.get('frame_topic') == 'self-evaluation'
                and self_eval_variant_meta.get('frame_goal') == 'clarify'
                and self_eval_variant_meta.get('frame_type') == 'self_inquiry'
                and self_eval_variant_meta.get('clarify_reason_code') == 'self-evaluation-request'
                and self_eval_variant_frame.get('topic') == 'self-evaluation'
            ),
        },
        {
            'name': 'shame_self_contempt_variants_use_same_frame_family',
            'pass': (
                shame_rc == 0
                and shame_variant_rc == 0
                and shame.get('decision_type') == 'clarify'
                and shame.get('delivery_mode') == 'final_text'
                and shame.get('allow_model_call') is False
                and shame_meta.get('frame_topic') == 'shame-self-contempt'
                and shame_meta.get('frame_goal') == 'clarify'
                and shame_meta.get('frame_type') == 'shame_self_contempt'
                and shame_meta.get('clarify_reason_code') == 'shame-self-contempt-request'
                and shame_frame.get('topic') == 'shame-self-contempt'
                and shame_variant_meta.get('frame_topic') == 'shame-self-contempt'
                and shame_variant_meta.get('frame_goal') == 'clarify'
                and shame_variant_meta.get('frame_type') == 'shame_self_contempt'
                and shame_variant_meta.get('clarify_reason_code') == 'shame-self-contempt-request'
                and shame_variant_frame.get('topic') == 'shame-self-contempt'
            ),
        },
        {
            'name': 'semantic_paraphrases_still_map_into_frame_families',
            'pass': (
                foundations_semantic_rc == 0
                and foundations_semantic_meta.get('frame_topic') == 'relationship-foundations'
                and foundations_semantic_meta.get('frame_goal') == 'overview'
                and foundations_semantic_frame.get('topic') == 'relationship-foundations'
                and lost_semantic_rc == 0
                and lost_semantic_meta.get('frame_topic') == 'lost-and-aimless'
                and lost_semantic_meta.get('frame_goal') == 'clarify'
                and lost_semantic_frame.get('topic') == 'lost-and-aimless'
                and self_eval_semantic_rc == 0
                and self_eval_semantic_meta.get('frame_topic') == 'self-evaluation'
                and self_eval_semantic_meta.get('frame_goal') == 'clarify'
                and self_eval_semantic_frame.get('topic') == 'self-evaluation'
                and shame_semantic_rc == 0
                and shame_semantic_meta.get('frame_topic') == 'shame-self-contempt'
                and shame_semantic_meta.get('frame_goal') == 'clarify'
                and shame_semantic_frame.get('topic') == 'shame-self-contempt'
            ),
        },
    ]

    emit_report(
        results,
        samples={
            'seed': seed,
            'followup': follow,
            'foundations': foundations,
            'lost_and_aimless': lost,
            'foundations_variant': foundations_variant,
            'marriage_variant': marriage_variant,
            'menu_variant': menu_variant,
            'menu_variant_two': menu_variant_two,
            'self_eval': self_eval,
            'self_eval_variant': self_eval_variant,
            'shame': shame,
            'shame_variant': shame_variant,
            'foundations_semantic': foundations_semantic,
            'lost_semantic': lost_semantic,
            'self_eval_semantic': self_eval_semantic,
            'shame_semantic': shame_semantic,
            'greeting': greeting,
            'small_talk': small_talk,
            'address': address,
            'sharing': sharing,
            'life_direction': life_direction,
            'slang_greeting': slang_greeting,
            'renderer_check': renderer_check,
            'appearance': appearance,
        },
        stderr={
            'seed': seed_stderr,
            'followup': follow_stderr,
            'foundations': foundations_stderr,
            'lost_and_aimless': lost_stderr,
            'foundations_variant': foundations_variant_stderr,
            'marriage_variant': marriage_variant_stderr,
            'menu_variant': menu_variant_stderr,
            'menu_variant_two': menu_variant_two_stderr,
            'self_eval': self_eval_stderr,
            'self_eval_variant': self_eval_variant_stderr,
            'shame': shame_stderr,
            'shame_variant': shame_variant_stderr,
            'foundations_semantic': foundations_semantic_stderr,
            'lost_semantic': lost_semantic_stderr,
            'self_eval_semantic': self_eval_semantic_stderr,
            'shame_semantic': shame_semantic_stderr,
            'greeting': greeting_stderr,
            'small_talk': small_talk_stderr,
            'address': address_stderr,
            'sharing': sharing_stderr,
            'life_direction': life_direction_stderr,
            'slang_greeting': slang_greeting_stderr,
            'renderer_check': renderer_check_stderr,
            'appearance': appearance_stderr,
        },
    )


if __name__ == '__main__':
    main()
