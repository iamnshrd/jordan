"""LLM renderer helpers backed by the official Anthropic Messages API."""
from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request as request_module

from library.config import resolve_jordan_model_ref


_DEFAULT_ANTHROPIC_ENDPOINT = 'https://api.anthropic.com/v1/messages'
_DEFAULT_ANTHROPIC_VERSION = '2023-06-01'
_DEFAULT_ANTHROPIC_MODEL = 'claude-sonnet-4-6'


def _resolve_api_key() -> str:
    for env_key in (
        'JORDAN_ANTHROPIC_API_KEY',
        'ANTHROPIC_API_KEY',
    ):
        value = (os.environ.get(env_key) or '').strip()
        if value:
            return value
    return ''


def _resolve_endpoint() -> str:
    explicit = (
        os.environ.get('JORDAN_ANTHROPIC_API_URL')
        or os.environ.get('ANTHROPIC_API_URL')
        or ''
    ).strip()
    if explicit:
        return explicit
    return _DEFAULT_ANTHROPIC_ENDPOINT


def _resolve_version() -> str:
    explicit = (os.environ.get('JORDAN_ANTHROPIC_VERSION') or '').strip()
    if explicit:
        return explicit
    return _DEFAULT_ANTHROPIC_VERSION


def _resolve_model_id() -> str:
    for env_key in (
        'JORDAN_LLM_RENDERER_MODEL_ID',
        'JORDAN_ANTHROPIC_MODEL',
        'ANTHROPIC_MODEL',
    ):
        raw = (os.environ.get(env_key) or '').strip()
        if raw:
            return raw
    model_ref = resolve_jordan_model_ref().strip()
    if '/' in model_ref:
        provider, model_id = model_ref.split('/', 1)
        if provider == 'anthropic' and model_id.strip():
            return model_id.strip()
    if model_ref.startswith('claude-'):
        return model_ref
    return _DEFAULT_ANTHROPIC_MODEL


def is_available() -> bool:
    if str(os.environ.get('JORDAN_DISABLE_ANTHROPIC_API_RENDERER') or '').strip().lower() in {
        '1', 'true', 'yes',
    }:
        return False
    return bool(_resolve_api_key())


def describe_anthropic_backend() -> str:
    return f'{_resolve_endpoint()} model={_resolve_model_id()}'


def _extract_output_text(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ''
    content = payload.get('content')
    if not isinstance(content, list):
        return ''
    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get('type') != 'text':
            continue
        text = item.get('text')
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    return '\n'.join(parts).strip()


def _call_anthropic_text(*, prompt: dict[str, str], timeout_seconds: float, max_tokens: int) -> str:
    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError('Anthropic API renderer missing API key.')

    headers = {
        'x-api-key': api_key,
        'anthropic-version': _resolve_version(),
        'content-type': 'application/json',
        'accept': 'application/json',
    }
    payload = {
        'model': _resolve_model_id(),
        'max_tokens': max_tokens,
        'system': str(prompt.get('system') or ''),
        'messages': [
            {
                'role': 'user',
                'content': str(prompt.get('user') or '').strip(),
            },
        ],
    }
    req = request_module.Request(
        _resolve_endpoint(),
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST',
    )
    try:
        with request_module.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
    except error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'Anthropic API renderer HTTP {exc.code}: {detail[:500]}') from exc
    except error.URLError as exc:
        raise RuntimeError(f'Anthropic API renderer connection failed: {exc}') from exc

    try:
        payload = json.loads(raw)
    except Exception as exc:
        raise RuntimeError(f'Anthropic API renderer returned non-JSON payload: {raw[:500]}') from exc
    text = _extract_output_text(payload)
    if not text:
        raise RuntimeError(
            'Anthropic API renderer returned no text payload: '
            f'{json.dumps(payload, ensure_ascii=False)[:500]}'
        )
    return text


def call_anthropic_json(*, prompt: dict[str, str], timeout_seconds: float, max_tokens: int = 220) -> dict[str, Any]:
    text = _call_anthropic_text(
        prompt=prompt,
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
    )
    stripped = (text or '').strip()
    try:
        payload = json.loads(stripped)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        start = stripped.find('{')
        end = stripped.rfind('}')
        if start >= 0 and end > start:
            try:
                payload = json.loads(stripped[start:end + 1])
                return payload if isinstance(payload, dict) else {}
            except Exception:
                return {}
    return {}


def render_via_anthropic_api(*, request, prompt, attempt, violations):
    timeout = float((os.environ.get('JORDAN_LLM_RENDERER_TIMEOUT_SECONDS') or '6').strip() or '6')
    return _call_anthropic_text(
        prompt=prompt,
        timeout_seconds=timeout,
        max_tokens=320,
    )


render_via_anthropic_api.__jordan_renderer_backend_detail__ = describe_anthropic_backend
