"""LLM renderer hook backed by the local OpenClaw CLI embedded runner."""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from library._core.runtime.openclaw_gateway_renderer import (
    _load_openclaw_config,
    _resolve_openclaw_config_path,
)


subprocess_module = subprocess


def _resolve_cli_bin() -> str:
    explicit = (os.environ.get('OPENCLAW_CLI_BIN') or '').strip()
    if explicit:
        return explicit
    return 'openclaw'


def _resolve_renderer_agent_id() -> str:
    return (os.environ.get('JORDAN_LLM_RENDERER_AGENT_ID') or 'main').strip() or 'main'


def is_available() -> bool:
    if str(os.environ.get('JORDAN_DISABLE_OPENCLAW_CLI_RENDERER') or '').strip().lower() in {
        '1', 'true', 'yes',
    }:
        return False
    if not (
        os.environ.get('OPENCLAW_CONFIG_PATH')
        or os.environ.get('OPENCLAW_STATE_DIR')
        or os.environ.get('OPENCLAW_JORDAN_BRIDGE_CWD')
        or str(os.environ.get('JORDAN_ENABLE_OPENCLAW_CLI_RENDERER') or '').strip().lower() in {
            '1', 'true', 'yes',
        }
    ):
        return False
    if not shutil.which(_resolve_cli_bin()):
        return False
    return bool(_load_openclaw_config())


def describe_cli_backend() -> str:
    return f'{_resolve_cli_bin()} agent --agent {_resolve_renderer_agent_id()} --local --json'


def _build_render_config(*, system_prompt: str) -> tuple[dict[str, Any], Path]:
    cfg = copy.deepcopy(_load_openclaw_config())
    if not isinstance(cfg, dict):
        cfg = {}
    agents = cfg.setdefault('agents', {})
    if not isinstance(agents, dict):
        agents = {}
        cfg['agents'] = agents
    defaults = agents.setdefault('defaults', {})
    if not isinstance(defaults, dict):
        defaults = {}
        agents['defaults'] = defaults
    defaults['systemPromptOverride'] = system_prompt
    defaults['skills'] = []
    return cfg, _resolve_openclaw_config_path()


def _extract_text(payload: dict[str, Any]) -> str:
    payloads = payload.get('payloads')
    if isinstance(payloads, list):
        for item in payloads:
            if not isinstance(item, dict):
                continue
            text = item.get('text')
            if isinstance(text, str) and text.strip():
                return text.strip()
    summary = payload.get('summary')
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    return ''


def render_via_openclaw_cli(*, request, prompt, attempt, violations):
    config, source_config_path = _build_render_config(system_prompt=prompt.get('system', ''))
    with tempfile.TemporaryDirectory(prefix='jordan-renderer-openclaw-') as temp_dir:
        temp_config_path = Path(temp_dir) / 'openclaw-renderer.json'
        temp_config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')

        env = os.environ.copy()
        env['OPENCLAW_CONFIG_PATH'] = str(temp_config_path)
        env.setdefault('OPENCLAW_HIDE_BANNER', '1')
        if source_config_path.exists():
            env.setdefault('OPENCLAW_RENDERER_SOURCE_CONFIG_PATH', str(source_config_path))

        timeout_seconds = float((os.environ.get('JORDAN_LLM_RENDERER_TIMEOUT_SECONDS') or '20').strip() or '20')
        command = [
            _resolve_cli_bin(),
            'agent',
            '--agent',
            _resolve_renderer_agent_id(),
            '--message',
            prompt.get('user', ''),
            '--local',
            '--json',
        ]
        completed = subprocess_module.run(
            command,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout_seconds,
            check=False,
        )
        stdout = (completed.stdout or '').strip()
        stderr = (completed.stderr or '').strip()
        if completed.returncode != 0:
            detail = stderr or stdout or f'exit code {completed.returncode}'
            raise RuntimeError(f'OpenClaw CLI renderer failed: {detail[:500]}')
        if not stdout:
            raise RuntimeError('OpenClaw CLI renderer returned empty stdout.')
        try:
            payload = json.loads(stdout)
        except Exception as exc:
            raise RuntimeError(f'OpenClaw CLI renderer returned non-JSON stdout: {stdout[:500]}') from exc
        if not isinstance(payload, dict):
            raise RuntimeError('OpenClaw CLI renderer returned a non-object JSON payload.')
        text = _extract_text(payload)
        if not text:
            raise RuntimeError(
                f'OpenClaw CLI renderer returned no text payload: {json.dumps(payload, ensure_ascii=False)[:500]}'
            )
        return text
