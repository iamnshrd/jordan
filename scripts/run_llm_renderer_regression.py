#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from _helpers import emit_report
from library._core.runtime.clarify_human import build_clarification
from library._core.runtime.llm_renderer import reset_llm_renderer, set_llm_renderer


def main() -> None:
    original_disable = os.environ.get('JORDAN_DISABLE_OPENCLAW_GATEWAY_RENDERER')
    original_hook = os.environ.get('JORDAN_LLM_RENDERER_HOOK')
    os.environ['JORDAN_DISABLE_OPENCLAW_GATEWAY_RENDERER'] = '1'
    os.environ.pop('JORDAN_LLM_RENDERER_HOOK', None)
    reset_llm_renderer()
    not_configured = build_clarification(
        'В чем заключается смысл крепких отношений?',
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
            'transition_kind': 'opening',
            'confidence': '0.9',
        },
        dialogue_act='open_topic',
    )

    os.environ['JORDAN_LLM_RENDERER_HOOK'] = 'library._core.runtime._llm_renderer_test_hook:render_text'
    os.environ['JORDAN_DISABLE_OPENCLAW_GATEWAY_RENDERER'] = '0'
    reset_llm_renderer()
    env_hook = build_clarification(
        'В чем заключается смысл крепких отношений?',
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
            'transition_kind': 'opening',
            'confidence': '0.9',
        },
        dialogue_act='open_topic',
    )

    os.environ['JORDAN_DISABLE_OPENCLAW_GATEWAY_RENDERER'] = '1'
    os.environ.pop('JORDAN_LLM_RENDERER_HOOK', None)
    captured: list[dict] = []

    def successful_renderer(*, request, prompt, attempt, violations):
        captured.append({
            'request': request.as_dict(),
            'prompt': prompt,
            'attempt': attempt,
            'violations': list(violations),
        })
        return 'Если говорить в общем виде, крепкие отношения держатся на правде, уважении и добровольной ответственности. Что из этого ты хочешь разобрать глубже?'

    set_llm_renderer(successful_renderer)
    success = build_clarification(
        'В чем заключается смысл крепких отношений?',
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
            'transition_kind': 'opening',
            'confidence': '0.9',
        },
        dialogue_act='open_topic',
    )
    reset_llm_renderer()

    axis_captured: list[dict] = []

    def axis_renderer(*, request, prompt, attempt, violations):
        axis_captured.append({
            'request': request.as_dict(),
            'prompt': prompt,
            'attempt': attempt,
            'violations': list(violations),
        })
        return 'Если держаться именно этой линии, обида редко живёт отдельно: обычно под ней уже лежит удар по достоинству. Где здесь больнее всего: в унижении или в холоде?'

    set_llm_renderer(axis_renderer)
    axis_followup = build_clarification(
        'скорее обида',
        dialogue_state={
            'active_topic': 'relationship-loss-of-feeling',
            'active_route': 'relationship-maintenance',
            'abstraction_level': 'general',
            'pending_slot': 'analysis_focus',
            'active_axis': '',
            'active_detail': '',
        },
        dialogue_frame={
            'topic': 'relationship-loss-of-feeling',
            'route': 'relationship-maintenance',
            'frame_type': 'relationship_general',
            'stance': 'general',
            'goal': 'clarify',
            'axis': '',
            'detail': '',
            'pending_slot': 'analysis_focus',
            'relation_to_previous': 'answer_slot',
            'transition_kind': 'axis_answer',
            'confidence': '0.9',
        },
        dialogue_act='supply_narrowing_axis',
        selected_axis='resentment',
    )
    reset_llm_renderer()

    retry_calls: list[dict] = []

    def retry_renderer(*, request, prompt, attempt, violations):
        retry_calls.append({'attempt': attempt, 'violations': list(violations)})
        if attempt == 1:
            return 'Хорошо, давай разберём это по-настоящему.'
        return 'Тогда не будем держать тему туманной и назовём её основу прямо. Что здесь для тебя важнее всего: правда, уважение или добровольно принятое общее бремя?'

    set_llm_renderer(retry_renderer)
    retry = build_clarification(
        'Какие могут быть причины потери чувств в серьезных отношениях?',
        dialogue_state={
            'active_topic': '',
            'active_route': 'relationship-maintenance',
            'abstraction_level': 'personal',
            'pending_slot': '',
            'active_axis': '',
            'active_detail': '',
        },
        dialogue_frame={
            'topic': 'relationship-loss-of-feeling',
            'route': 'relationship-maintenance',
            'frame_type': 'relationship_problem',
            'stance': 'personal',
            'goal': 'clarify',
            'axis': '',
            'detail': '',
            'pending_slot': 'narrowing_axis',
            'relation_to_previous': 'new',
            'transition_kind': 'opening',
            'confidence': '0.9',
        },
        dialogue_act='open_topic',
    )
    reset_llm_renderer()

    fallback_calls: list[dict] = []

    def failing_renderer(*, request, prompt, attempt, violations):
        fallback_calls.append({'attempt': attempt, 'violations': list(violations)})
        if attempt == 1:
            return 'Book source quote.'
        return 'Хорошо, source.'

    set_llm_renderer(failing_renderer)
    fallback = build_clarification(
        'и что с этим делать?',
        dialogue_state={
            'active_topic': 'self-diagnosis',
            'active_route': 'general',
            'abstraction_level': 'personal',
            'pending_slot': 'next_step',
            'active_axis': 'emotional_flatness',
            'active_detail': 'social_disconnection',
        },
        dialogue_frame={
            'topic': 'self-diagnosis',
            'route': 'general',
            'frame_type': 'self_diagnosis_soft',
            'stance': 'personal',
            'goal': 'next_step',
            'axis': 'emotional_flatness',
            'detail': 'social_disconnection',
            'pending_slot': 'example_or_shift',
            'relation_to_previous': 'continue',
            'transition_kind': 'next_step',
            'confidence': '0.9',
        },
        dialogue_act='open_topic',
    )
    reset_llm_renderer()

    success_meta = success.metadata or {}
    not_configured_meta = not_configured.metadata or {}
    env_hook_meta = env_hook.metadata or {}
    axis_meta = axis_followup.metadata or {}
    retry_meta = retry.metadata or {}
    fallback_meta = fallback.metadata or {}

    results = [
        {
            'name': 'renderer_not_configured_does_not_count_as_runtime_fallback',
            'pass': (
                not_configured_meta.get('renderer_used') is False
                and not_configured_meta.get('renderer_status') == 'not_configured'
                and not_configured_meta.get('renderer_fallback_used') is False
            ),
        },
        {
            'name': 'renderer_builds_contract_and_returns_valid_text',
            'pass': (
                success_meta.get('renderer_used') is True
                and success_meta.get('renderer_status') == 'ok'
                and success_meta.get('renderer_attempt_count') == 1
                and success_meta.get('renderer_fallback_used') is False
                and success_meta.get('clarify_reason_code') == 'relationship-foundations-overview'
                and len(captured) == 1
                and captured[0]['request']['frame_topic'] == 'relationship-foundations'
                and captured[0]['request']['frame_goal'] == 'overview'
                and captured[0]['request']['render_kind'] == 'profile'
                and captured[0]['request']['ends_with_question'] is True
                and 'источники' in captured[0]['prompt']['user'].lower()
                and success.text.endswith('?')
            ),
        },
        {
            'name': 'renderer_autoloads_hook_from_env',
            'pass': (
                env_hook_meta.get('renderer_used') is True
                and env_hook_meta.get('renderer_status') == 'ok'
                and env_hook_meta.get('renderer_fallback_used') is False
                and 'добровольно принятой ответственности' in (env_hook.text or '').lower()
            ),
        },
        {
            'name': 'renderer_preserves_frame_goal_for_axis_followup',
            'pass': (
                axis_meta.get('renderer_status') == 'ok'
                and axis_meta.get('renderer_fallback_used') is False
                and len(axis_captured) == 1
                and axis_captured[0]['request']['frame_goal'] == 'clarify'
                and axis_captured[0]['request']['render_kind'] == 'axis_followup'
            ),
        },
        {
            'name': 'renderer_retries_on_forbidden_opener_then_accepts',
            'pass': (
                retry_meta.get('renderer_status') == 'ok'
                and retry_meta.get('renderer_attempt_count') == 2
                and retry_meta.get('renderer_fallback_used') is False
                and len(retry_calls) == 2
                and retry_calls[1]['violations'] == ['forbidden_opener', 'missing_final_question']
            ),
        },
        {
            'name': 'renderer_falls_back_after_second_invalid_attempt',
            'pass': (
                fallback_meta.get('renderer_status') == 'validation_failed_fallback'
                and fallback_meta.get('renderer_attempt_count') == 2
                and fallback_meta.get('renderer_fallback_used') is True
                and 'forbidden_opener' in (fallback_meta.get('renderer_validation_failures') or [])
                and fallback.text != 'Book source quote.'
                and 'book' not in fallback.text.lower()
                and 'source' not in fallback.text.lower()
                and fallback_meta.get('clarify_reason_code') == 'self-diagnosis-next-step'
            ),
        },
    ]

    if original_disable is None:
        os.environ.pop('JORDAN_DISABLE_OPENCLAW_GATEWAY_RENDERER', None)
    else:
        os.environ['JORDAN_DISABLE_OPENCLAW_GATEWAY_RENDERER'] = original_disable
    if original_hook is None:
        os.environ.pop('JORDAN_LLM_RENDERER_HOOK', None)
    else:
        os.environ['JORDAN_LLM_RENDERER_HOOK'] = original_hook

    emit_report(
        results,
        not_configured_metadata=not_configured_meta,
        env_hook_metadata=env_hook_meta,
        success_metadata=success_meta,
        axis_metadata=axis_meta,
        retry_metadata=retry_meta,
        fallback_metadata=fallback_meta,
    )


if __name__ == '__main__':
    main()
