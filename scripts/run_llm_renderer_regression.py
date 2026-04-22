#!/usr/bin/env python3
from __future__ import annotations

import json
import io
import os
import sys
import tempfile
from urllib import error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from _helpers import emit_report
from library._core.runtime.clarify_human import build_clarification
from library._core.runtime.llm_renderer import reset_llm_renderer, set_llm_renderer
from library._core.runtime import openclaw_api_renderer
from library._core.runtime import openclaw_cli_renderer
from library._core.runtime import openclaw_gateway_renderer


def main() -> None:
    original_disable = os.environ.get('JORDAN_DISABLE_OPENCLAW_GATEWAY_RENDERER')
    original_hook = os.environ.get('JORDAN_LLM_RENDERER_HOOK')
    original_gateway_token = os.environ.get('OPENCLAW_GATEWAY_TOKEN')
    original_jordan_model = os.environ.get('JORDAN_MODEL')
    original_renderer_model = os.environ.get('JORDAN_LLM_RENDERER_MODEL')
    original_disable_cli = os.environ.get('JORDAN_DISABLE_OPENCLAW_CLI_RENDERER')
    original_disable_api = os.environ.get('JORDAN_DISABLE_OPENCLAW_API_RENDERER')
    original_openclaw_config_path = os.environ.get('OPENCLAW_CONFIG_PATH')
    original_openclaw_state_dir = os.environ.get('OPENCLAW_STATE_DIR')
    original_openclaw_cli_bin = os.environ.get('OPENCLAW_CLI_BIN')
    os.environ['JORDAN_DISABLE_OPENCLAW_GATEWAY_RENDERER'] = '1'
    os.environ['JORDAN_DISABLE_OPENCLAW_CLI_RENDERER'] = '1'
    os.environ['JORDAN_DISABLE_OPENCLAW_API_RENDERER'] = '1'
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

    def exploding_renderer(*, request, prompt, attempt, violations):
        raise RuntimeError('simulated gateway failure')

    set_llm_renderer(exploding_renderer)
    exception_case = build_clarification(
        'Добрый вечер, Джордан',
        dialogue_state={
            'active_topic': '',
            'active_route': 'general',
            'abstraction_level': 'general',
            'pending_slot': '',
            'active_axis': '',
            'active_detail': '',
        },
        dialogue_frame={
            'topic': 'greeting',
            'route': 'general',
            'frame_type': 'greeting',
            'stance': 'general',
            'goal': 'opening',
            'axis': '',
            'detail': '',
            'pending_slot': '',
            'relation_to_previous': 'new',
            'transition_kind': 'opening',
            'confidence': '0.9',
        },
        dialogue_act='greeting_opening',
    )
    reset_llm_renderer()

    gateway_calls: list[dict] = []
    gateway_fallback_calls: list[dict] = []
    api_calls: list[dict] = []
    original_urlopen = openclaw_gateway_renderer.request_module.urlopen
    original_api_urlopen = openclaw_api_renderer.request_module.urlopen
    os.environ['OPENCLAW_GATEWAY_TOKEN'] = 'test-token'
    os.environ['JORDAN_MODEL'] = 'openai-codex/gpt-5.4'
    os.environ.pop('JORDAN_LLM_RENDERER_MODEL', None)

    class _FakeGatewayResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({'output_text': 'Тогда держись главного узла и назови его прямо.'}).encode('utf-8')

    def _fake_urlopen(req, timeout=0):
        gateway_calls.append({
            'timeout': timeout,
            'headers': dict(req.header_items()),
            'body': json.loads(req.data.decode('utf-8')),
            'url': req.full_url,
        })
        return _FakeGatewayResponse()

    class _FakeApiResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        @property
        def headers(self):
            return {'content-type': 'text/event-stream'}

        def read(self):
            return (
                'data: {"type":"response.output_item.done","item":{"type":"message","role":"assistant","status":"completed","content":[{"type":"output_text","text":"Скажи прямо, что именно ты хочешь разобрать.","annotations":[]}]}}\n\n'
                'data: {"type":"response.completed","response":{"status":"completed","usage":{"input_tokens":10,"output_tokens":10,"total_tokens":20}}}\n\n'
                'data: [DONE]\n\n'
            ).encode('utf-8')

    def _fake_api_urlopen(req, timeout=0):
        api_calls.append({
            'timeout': timeout,
            'headers': dict(req.header_items()),
            'body': json.loads(req.data.decode('utf-8')),
            'url': req.full_url,
        })
        return _FakeApiResponse()

    class _FakeChatCompletionResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({
                'choices': [
                    {
                        'message': {
                            'content': 'Смотри на главный узел и назови его прямо.',
                        },
                    },
                ],
            }).encode('utf-8')

    def _fake_urlopen_with_fallback(req, timeout=0):
        gateway_fallback_calls.append({
            'timeout': timeout,
            'headers': dict(req.header_items()),
            'body': json.loads(req.data.decode('utf-8')),
            'url': req.full_url,
        })
        if req.full_url.endswith('/v1/responses'):
            raise error.HTTPError(
                req.full_url,
                404,
                'Not Found',
                hdrs=None,
                fp=io.BytesIO(b'Not Found'),
            )
        return _FakeChatCompletionResponse()

    openclaw_gateway_renderer.request_module.urlopen = _fake_urlopen
    try:
        gateway_rendered = openclaw_gateway_renderer.render_via_openclaw_gateway(
            request=None,
            prompt={'system': 'sys', 'user': 'usr'},
            attempt=1,
            violations=[],
        )
    finally:
        openclaw_gateway_renderer.request_module.urlopen = original_urlopen

    with tempfile.TemporaryDirectory(prefix='jordan-openclaw-api-renderer-') as temp_dir:
        state_dir = Path(temp_dir) / 'state'
        auth_dir = state_dir / 'agents' / 'main' / 'agent'
        auth_dir.mkdir(parents=True, exist_ok=True)
        auth_store_path = auth_dir / 'auth-profiles.json'
        auth_store_path.write_text(
            json.dumps(
                {
                    'version': 1,
                    'profiles': {
                        'openai-codex:default': {
                            'type': 'oauth',
                            'provider': 'openai-codex',
                            'access': 'oauth-access',
                            'refresh': 'oauth-refresh',
                            'expires': 9999999999999,
                            'accountId': 'acct_test_123',
                        },
                    },
                },
                ensure_ascii=False,
            ),
            encoding='utf-8',
        )
        os.environ['OPENCLAW_STATE_DIR'] = str(state_dir)
        os.environ['JORDAN_DISABLE_OPENCLAW_API_RENDERER'] = '0'
        openclaw_api_renderer.request_module.urlopen = _fake_api_urlopen
        try:
            api_rendered = openclaw_api_renderer.render_via_openclaw_api(
                request=None,
                prompt={'system': 'sys', 'user': 'USER'},
                attempt=1,
                violations=[],
            )
        finally:
            openclaw_api_renderer.request_module.urlopen = original_api_urlopen

    openclaw_gateway_renderer.request_module.urlopen = _fake_urlopen_with_fallback
    try:
        gateway_fallback_rendered = openclaw_gateway_renderer.render_via_openclaw_gateway(
            request=None,
            prompt={'system': 'sys', 'user': 'usr'},
            attempt=1,
            violations=[],
        )
    finally:
        openclaw_gateway_renderer.request_module.urlopen = original_urlopen

    with tempfile.TemporaryDirectory(prefix='jordan-openclaw-cli-renderer-') as temp_dir:
        config_path = Path(temp_dir) / 'openclaw.json'
        config_path.write_text(
            json.dumps({'agents': {'defaults': {'model': {'primary': 'openai-codex/gpt-5.4'}}}}, ensure_ascii=False),
            encoding='utf-8',
        )
        os.environ['OPENCLAW_CONFIG_PATH'] = str(config_path)
        os.environ['OPENCLAW_CLI_BIN'] = '/usr/bin/openclaw'
        os.environ['JORDAN_DISABLE_OPENCLAW_CLI_RENDERER'] = '0'

        cli_calls: list[dict] = []
        original_subprocess_run = openclaw_cli_renderer.subprocess_module.run

        class _FakeCompleted:
            def __init__(self, stdout: str, stderr: str = '', returncode: int = 0):
                self.stdout = stdout
                self.stderr = stderr
                self.returncode = returncode

        def _fake_subprocess_run(command, *, capture_output, text, env, timeout, check):
            cli_calls.append({
                'command': list(command),
                'env_config_path': env.get('OPENCLAW_CONFIG_PATH'),
                'timeout': timeout,
            })
            return _FakeCompleted(json.dumps({'payloads': [{'text': 'Привет.'}], 'meta': {}}))

        openclaw_cli_renderer.subprocess_module.run = _fake_subprocess_run
        try:
            cli_rendered = openclaw_cli_renderer.render_via_openclaw_cli(
                request=None,
                prompt={'system': 'SYSTEM', 'user': 'USER'},
                attempt=1,
                violations=[],
            )
        finally:
            openclaw_cli_renderer.subprocess_module.run = original_subprocess_run

    success_meta = success.metadata or {}
    not_configured_meta = not_configured.metadata or {}
    env_hook_meta = env_hook.metadata or {}
    axis_meta = axis_followup.metadata or {}
    retry_meta = retry.metadata or {}
    fallback_meta = fallback.metadata or {}
    exception_meta = exception_case.metadata or {}

    results = [
        {
            'name': 'openclaw_api_renderer_uses_oauth_profile_and_codex_backend',
            'pass': (
                api_rendered == 'Скажи прямо, что именно ты хочешь разобрать.'
                and len(api_calls) == 1
                and api_calls[0]['url'] == 'https://chatgpt.com/backend-api/codex/responses'
                and api_calls[0]['body']['model'] == 'gpt-5.4'
                and isinstance(api_calls[0]['body'].get('input'), list)
                and api_calls[0]['body']['input'][0]['role'] == 'user'
                and api_calls[0]['body']['input'][0]['content'][0]['type'] == 'input_text'
                and api_calls[0]['body']['input'][0]['content'][0]['text'] == 'USER'
                and api_calls[0]['body']['stream'] is True
                and api_calls[0]['body']['store'] is False
                and api_calls[0]['headers'].get('Authorization') == 'Bearer oauth-access'
                and api_calls[0]['headers'].get('Chatgpt-account-id') == 'acct_test_123'
            ),
        },
        {
            'name': 'gateway_renderer_uses_jordan_model_override_header',
            'pass': (
                gateway_rendered == 'Тогда держись главного узла и назови его прямо.'
                and len(gateway_calls) == 1
                and gateway_calls[0]['body']['model'] == 'openclaw'
                and gateway_calls[0]['headers'].get('X-openclaw-model') == 'openai-codex/gpt-5.4'
            ),
        },
        {
            'name': 'gateway_renderer_falls_back_to_chat_completions_on_404',
            'pass': (
                gateway_fallback_rendered == 'Смотри на главный узел и назови его прямо.'
                and len(gateway_fallback_calls) == 2
                and gateway_fallback_calls[0]['url'].endswith('/v1/responses')
                and gateway_fallback_calls[1]['url'].endswith('/v1/chat/completions')
                and gateway_fallback_calls[1]['body']['model'] == 'openclaw'
                and gateway_fallback_calls[1]['headers'].get('X-openclaw-model') == 'openai-codex/gpt-5.4'
            ),
        },
        {
            'name': 'openclaw_cli_renderer_uses_local_agent_json_path',
            'pass': (
                cli_rendered == 'Привет.'
                and len(cli_calls) == 1
                and cli_calls[0]['command'] == [
                    '/usr/bin/openclaw',
                    'agent',
                    '--agent',
                    'main',
                    '--message',
                    'USER',
                    '--local',
                    '--json',
                ]
                and cli_calls[0]['env_config_path'] != str(config_path)
            ),
        },
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
        {
            'name': 'renderer_exception_detail_reaches_metadata',
            'pass': (
                exception_meta.get('renderer_status') == 'exception_fallback'
                and exception_meta.get('renderer_fallback_used') is True
                and 'RuntimeError: simulated gateway failure' in (
                    exception_meta.get('renderer_exception_detail') or ''
                )
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
    if original_gateway_token is None:
        os.environ.pop('OPENCLAW_GATEWAY_TOKEN', None)
    else:
        os.environ['OPENCLAW_GATEWAY_TOKEN'] = original_gateway_token
    if original_jordan_model is None:
        os.environ.pop('JORDAN_MODEL', None)
    else:
        os.environ['JORDAN_MODEL'] = original_jordan_model
    if original_renderer_model is None:
        os.environ.pop('JORDAN_LLM_RENDERER_MODEL', None)
    else:
        os.environ['JORDAN_LLM_RENDERER_MODEL'] = original_renderer_model
    if original_disable_cli is None:
        os.environ.pop('JORDAN_DISABLE_OPENCLAW_CLI_RENDERER', None)
    else:
        os.environ['JORDAN_DISABLE_OPENCLAW_CLI_RENDERER'] = original_disable_cli
    if original_disable_api is None:
        os.environ.pop('JORDAN_DISABLE_OPENCLAW_API_RENDERER', None)
    else:
        os.environ['JORDAN_DISABLE_OPENCLAW_API_RENDERER'] = original_disable_api
    if original_openclaw_config_path is None:
        os.environ.pop('OPENCLAW_CONFIG_PATH', None)
    else:
        os.environ['OPENCLAW_CONFIG_PATH'] = original_openclaw_config_path
    if original_openclaw_state_dir is None:
        os.environ.pop('OPENCLAW_STATE_DIR', None)
    else:
        os.environ['OPENCLAW_STATE_DIR'] = original_openclaw_state_dir
    if original_openclaw_cli_bin is None:
        os.environ.pop('OPENCLAW_CLI_BIN', None)
    else:
        os.environ['OPENCLAW_CLI_BIN'] = original_openclaw_cli_bin

    emit_report(
        results,
        not_configured_metadata=not_configured_meta,
        env_hook_metadata=env_hook_meta,
        success_metadata=success_meta,
        axis_metadata=axis_meta,
        retry_metadata=retry_meta,
        fallback_metadata=fallback_meta,
        exception_metadata=exception_meta,
    )


if __name__ == '__main__':
    main()
