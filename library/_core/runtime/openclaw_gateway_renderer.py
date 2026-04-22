"""LLM renderer hook backed by the local OpenClaw gateway."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib import error, parse, request


_DEFAULT_GATEWAY_URL = 'http://127.0.0.1:18789'
_DEFAULT_MODEL = 'openclaw'


def _resolve_openclaw_config_path() -> Path:
    raw = (os.environ.get('OPENCLAW_CONFIG_PATH') or '').strip()
    if raw:
        return Path(raw).expanduser()
    state_dir = (os.environ.get('OPENCLAW_STATE_DIR') or '').strip()
    if state_dir:
        return Path(state_dir).expanduser() / 'openclaw.json'
    profile = (os.environ.get('OPENCLAW_PROFILE') or '').strip()
    if profile:
        return Path(f'~/.openclaw-{profile}/openclaw.json').expanduser()
    return Path('~/.openclaw/openclaw.json').expanduser()


def _load_openclaw_config() -> dict[str, Any]:
    path = _resolve_openclaw_config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _get_nested(mapping: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _normalize_gateway_url(raw_url: str) -> str:
    url = (raw_url or '').strip() or _DEFAULT_GATEWAY_URL
    parsed = parse.urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme == 'ws':
        scheme = 'http'
    elif scheme == 'wss':
        scheme = 'https'
    elif not scheme:
        scheme = 'http'
    netloc = parsed.netloc or parsed.path or '127.0.0.1:18789'
    return parse.urlunparse((scheme, netloc, '', '', '', ''))


def resolve_gateway_url() -> str:
    return resolve_gateway_url_with_source()[0]


def resolve_gateway_url_with_source() -> tuple[str, str]:
    env_url = (
        os.environ.get('JORDAN_LLM_RENDERER_GATEWAY_URL')
        or os.environ.get('OPENCLAW_GATEWAY_URL')
        or ''
    ).strip()
    if env_url:
        return _normalize_gateway_url(env_url), 'env'
    cfg = _load_openclaw_config()
    cfg_url = _get_nested(cfg, ('gateway', 'remote', 'url'))
    if isinstance(cfg_url, str) and cfg_url.strip():
        return _normalize_gateway_url(cfg_url), 'config'
    return _normalize_gateway_url(_DEFAULT_GATEWAY_URL), 'default'


def resolve_gateway_secret() -> str:
    env_token = (os.environ.get('OPENCLAW_GATEWAY_TOKEN') or '').strip()
    if env_token:
        return env_token
    env_password = (os.environ.get('OPENCLAW_GATEWAY_PASSWORD') or '').strip()
    if env_password:
        return env_password
    cfg = _load_openclaw_config()
    auth_mode = str(_get_nested(cfg, ('gateway', 'auth', 'mode')) or '').strip().lower()
    cfg_token = _get_nested(cfg, ('gateway', 'auth', 'token'))
    cfg_password = _get_nested(cfg, ('gateway', 'auth', 'password'))
    token = cfg_token.strip() if isinstance(cfg_token, str) else ''
    password = cfg_password.strip() if isinstance(cfg_password, str) else ''
    if auth_mode == 'password':
        return password or token
    return token or password


def is_available() -> bool:
    if str(os.environ.get('JORDAN_DISABLE_OPENCLAW_GATEWAY_RENDERER') or '').strip().lower() in {
        '1', 'true', 'yes',
    }:
        return False
    return bool(resolve_gateway_secret())


def describe_gateway_backend() -> str:
    gateway_url, source = resolve_gateway_url_with_source()
    return f'{source}:{gateway_url.rstrip("/")}/v1/responses'


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
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    text = part.get('text')
                    part_type = str(part.get('type') or '')
                    if part_type == 'output_text' and isinstance(text, str) and text.strip():
                        return text.strip()
        message = payload.get('message')
        if isinstance(message, str) and message.strip():
            return message.strip()
    return ''


def render_via_openclaw_gateway(*, request, prompt, attempt, violations):
    gateway_url = resolve_gateway_url().rstrip('/')
    secret = resolve_gateway_secret()
    if not secret:
        raise RuntimeError('OpenClaw gateway auth token/password is not configured.')
    body = {
        'model': (os.environ.get('JORDAN_LLM_RENDERER_MODEL') or _DEFAULT_MODEL).strip() or _DEFAULT_MODEL,
        'instructions': prompt.get('system', ''),
        'input': prompt.get('user', ''),
        'store': False,
    }
    req = request_module.Request(
        f'{gateway_url}/v1/responses',
        data=json.dumps(body).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {secret}',
        },
        method='POST',
    )
    timeout = float((os.environ.get('JORDAN_LLM_RENDERER_TIMEOUT_SECONDS') or '20').strip() or '20')
    try:
        with request_module.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
    except error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'OpenClaw gateway renderer HTTP {exc.code}: {detail[:300]}') from exc
    except error.URLError as exc:
        raise RuntimeError(f'OpenClaw gateway renderer connection failed: {exc}') from exc
    payload = json.loads(raw)
    text = _extract_output_text(payload)
    if not text:
        raise RuntimeError('OpenClaw gateway renderer returned no output_text.')
    return text


# Alias to avoid shadowing imported ``request`` arg in renderer callback signature.
request_module = request

render_via_openclaw_gateway.__jordan_renderer_backend__ = 'openclaw_gateway'
render_via_openclaw_gateway.__jordan_renderer_backend_detail__ = describe_gateway_backend
