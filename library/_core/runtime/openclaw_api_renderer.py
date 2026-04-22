"""LLM renderer hook backed by direct OpenClaw-managed OpenAI Codex auth."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib import error, request as request_module

from library.config import resolve_jordan_model_ref
from library._core.runtime.openclaw_gateway_renderer import (
    _load_openclaw_config,
    _resolve_openclaw_config_path,
)


_DEFAULT_CODEX_RESPONSES_URL = 'https://chatgpt.com/backend-api/codex/responses'


def _resolve_state_dir() -> Path | None:
    explicit = (os.environ.get('OPENCLAW_STATE_DIR') or '').strip()
    if explicit:
        return Path(explicit).expanduser()
    config_path = _resolve_openclaw_config_path()
    if config_path.name == 'openclaw.json':
        return config_path.parent
    return None


def _resolve_agent_id() -> str:
    return (os.environ.get('JORDAN_LLM_RENDERER_AGENT_ID') or 'main').strip() or 'main'


def _resolve_auth_profiles_path() -> Path | None:
    state_dir = _resolve_state_dir()
    if state_dir is None:
        return None
    return state_dir / 'agents' / _resolve_agent_id() / 'agent' / 'auth-profiles.json'


def _load_auth_profiles() -> dict[str, Any]:
    path = _resolve_auth_profiles_path()
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _select_openai_codex_profile(store: dict[str, Any]) -> dict[str, Any] | None:
    profiles = store.get('profiles')
    if not isinstance(profiles, dict):
        return None
    preferred_ids: list[str] = []
    fallback_ids: list[str] = []
    for profile_id, credential in profiles.items():
        if not isinstance(profile_id, str) or not isinstance(credential, dict):
            continue
        if credential.get('provider') != 'openai-codex' or credential.get('type') != 'oauth':
            continue
        if isinstance(credential.get('access'), str) and credential.get('access', '').strip():
            if profile_id == 'openai-codex:default':
                preferred_ids.insert(0, profile_id)
            else:
                fallback_ids.append(profile_id)
    for profile_id in preferred_ids + sorted(fallback_ids):
        credential = profiles.get(profile_id)
        if isinstance(credential, dict):
            return credential
    return None


def _resolve_model_id() -> str:
    model_ref = resolve_jordan_model_ref().strip()
    if '/' in model_ref:
        provider, model_id = model_ref.split('/', 1)
        if provider == 'openai-codex' and model_id.strip():
            return model_id.strip()
    explicit = (os.environ.get('JORDAN_LLM_RENDERER_MODEL_ID') or '').strip()
    if explicit:
        return explicit
    return 'gpt-5.4'


def _resolve_endpoint() -> str:
    explicit = (os.environ.get('JORDAN_LLM_RENDERER_API_URL') or '').strip()
    if explicit:
        return explicit
    cfg = _load_openclaw_config()
    configured = (
        cfg.get('models', {})
        .get('providers', {})
        .get('openai-codex', {})
        .get('baseUrl')
    )
    if isinstance(configured, str) and configured.strip():
        return configured.rstrip('/') + '/responses'
    return _DEFAULT_CODEX_RESPONSES_URL


def is_available() -> bool:
    if str(os.environ.get('JORDAN_DISABLE_OPENCLAW_API_RENDERER') or '').strip().lower() in {
        '1', 'true', 'yes',
    }:
        return False
    credential = _select_openai_codex_profile(_load_auth_profiles())
    return bool(credential)


def describe_api_backend() -> str:
    return f'{_resolve_endpoint()} model={resolve_jordan_model_ref().strip() or _resolve_model_id()}'


def _extract_output_text(payload: Any) -> str:
    if isinstance(payload, dict):
        output_text = payload.get('output_text')
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()
        output = payload.get('output')
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get('content')
                if not isinstance(content, list):
                    continue
                parts: list[str] = []
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    if part.get('type') != 'output_text':
                        continue
                    text = part.get('text')
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
                if parts:
                    return ''.join(parts).strip()
    return ''


def _parse_sse_payload(raw: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for chunk in raw.split('\n\n'):
        chunk = chunk.strip()
        if not chunk:
            continue
        data_lines = [line[5:].strip() for line in chunk.splitlines() if line.startswith('data:')]
        if not data_lines:
            continue
        data = '\n'.join(data_lines).strip()
        if not data or data == '[DONE]':
            continue
        try:
            parsed = json.loads(data)
        except Exception:
            continue
        if isinstance(parsed, dict):
            events.append(parsed)
    return events


def _extract_output_text_from_sse(raw: str) -> str:
    deltas: list[str] = []
    fallback_items: list[dict[str, Any]] = []
    completed_response: dict[str, Any] | None = None
    for event in _parse_sse_payload(raw):
        event_type = event.get('type')
        if event_type == 'response.output_text.delta':
            delta = event.get('delta')
            if isinstance(delta, str) and delta:
                deltas.append(delta)
            continue
        if event_type == 'response.output_text.done':
            text = event.get('text')
            if isinstance(text, str) and text.strip():
                return text.strip()
            continue
        if event_type == 'response.output_item.done':
            item = event.get('item')
            if isinstance(item, dict):
                fallback_items.append(item)
            continue
        if event_type == 'response.completed':
            response = event.get('response')
            if isinstance(response, dict):
                completed_response = response
    if deltas:
        return ''.join(deltas).strip()
    for item in fallback_items:
        text = _extract_output_text({'output': [item]})
        if text:
            return text
    if completed_response is not None:
        text = _extract_output_text({'output': completed_response.get('output')})
        if text:
            return text
    return ''


def render_via_openclaw_api(*, request, prompt, attempt, violations):
    store = _load_auth_profiles()
    credential = _select_openai_codex_profile(store)
    if credential is None:
        raise RuntimeError('OpenClaw API renderer could not find an openai-codex oauth profile.')
    access = str(credential.get('access') or '').strip()
    if not access:
        raise RuntimeError('OpenClaw API renderer found an openai-codex profile without access token.')

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {access}',
    }
    account_id = str(credential.get('accountId') or '').strip()
    if account_id:
        headers['ChatGPT-Account-Id'] = account_id

    user_text = str(prompt.get('user') or '').strip()
    payload = {
        'model': _resolve_model_id(),
        'instructions': prompt.get('system', ''),
        'input': [
            {
                'role': 'user',
                'content': [{'type': 'input_text', 'text': user_text}],
            }
        ],
        'stream': True,
        'store': False,
        'text': {'verbosity': 'low'},
    }
    timeout = float((os.environ.get('JORDAN_LLM_RENDERER_TIMEOUT_SECONDS') or '6').strip() or '6')
    req = request_module.Request(
        _resolve_endpoint(),
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST',
    )
    try:
        with request_module.urlopen(req, timeout=timeout) as resp:
            content_type = str(resp.headers.get('content-type') or '')
            raw = resp.read().decode('utf-8', errors='replace')
    except error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'OpenClaw API renderer HTTP {exc.code}: {detail[:500]}') from exc
    except error.URLError as exc:
        raise RuntimeError(f'OpenClaw API renderer connection failed: {exc}') from exc

    if 'text/event-stream' in content_type or raw.lstrip().startswith('data:'):
        text = _extract_output_text_from_sse(raw)
        if not text:
            raise RuntimeError(
                'OpenClaw API renderer returned no output_text in SSE payload: '
                f'{raw[:500]}'
            )
        return text

    try:
        response_payload = json.loads(raw)
    except Exception as exc:
        raise RuntimeError(f'OpenClaw API renderer returned non-JSON payload: {raw[:500]}') from exc
    text = _extract_output_text(response_payload)
    if not text:
        raise RuntimeError(
            'OpenClaw API renderer returned no output_text payload: '
            f'{json.dumps(response_payload, ensure_ascii=False)[:500]}'
        )
    return text


render_via_openclaw_api.__jordan_renderer_backend_detail__ = describe_api_backend
