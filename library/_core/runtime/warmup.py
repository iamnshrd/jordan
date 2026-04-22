from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Any, Callable

from library._core.runtime.clarify_human import build_clarification
from library._core.runtime.llm_renderer import reset_llm_renderer
from library._core.runtime.openclaw_gateway_renderer import (
    is_available as is_gateway_renderer_available,
    render_via_openclaw_gateway,
)
from library.utils import log_event


_GREETING_FRAME = {
    'topic': 'greeting',
    'route': 'general',
    'frame_type': 'greeting',
    'stance': 'personal',
    'goal': 'opening',
    'axis': '',
    'detail': '',
    'pending_slot': '',
    'relation_to_previous': 'new',
    'transition_kind': 'opening',
    'confidence': 0.9,
}

_EMPTY_STATE = {
    'active_topic': '',
    'active_route': 'general',
    'abstraction_level': 'personal',
    'pending_slot': '',
    'active_axis': '',
    'active_detail': '',
}


@contextmanager
def _temporary_env(name: str, value: str):
    previous = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


def warm_local_clarification() -> dict[str, Any]:
    log_event('runtime.warmup_local_started', stage='warmup')
    reset_llm_renderer()
    with _temporary_env('JORDAN_DISABLE_OPENCLAW_GATEWAY_RENDERER', '1'):
        result = build_clarification(
            'Добрый вечер',
            dialogue_state=dict(_EMPTY_STATE),
            dialogue_frame=dict(_GREETING_FRAME),
            dialogue_act='open_topic',
        )
    reset_llm_renderer()
    payload = {
        'status': 'ok',
        'text_preview': (result.text or '')[:120],
        'clarify_profile': result.metadata.get('clarify_profile', ''),
    }
    log_event('runtime.warmup_local_finished', stage='warmup', **payload)
    return payload


def warm_renderer_path(
    *,
    timeout_seconds: float = 45.0,
    retry_interval: float = 2.0,
    render_fn: Callable[..., str] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    now_fn: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    if not is_gateway_renderer_available():
        payload = {
            'status': 'not_available',
            'attempt_count': 0,
            'text_preview': '',
            'exception_detail': '',
        }
        log_event('runtime.warmup_renderer_skipped', stage='warmup', **payload)
        return payload

    renderer = render_fn or render_via_openclaw_gateway
    deadline = now_fn() + max(timeout_seconds, 0.0)
    attempt_count = 0
    exception_detail = ''
    log_event(
        'runtime.warmup_renderer_started',
        stage='warmup',
        timeout_seconds=timeout_seconds,
        retry_interval=retry_interval,
    )
    while True:
        attempt_count += 1
        try:
            text = renderer(
                request=None,
                prompt={
                    'system': 'Сформулируй одно короткое естественное приветствие по-русски.',
                    'user': 'Скажи короткое приветствие по-русски без объяснений.',
                },
                attempt=attempt_count,
                violations=[],
            )
            payload = {
                'status': 'ok',
                'attempt_count': attempt_count,
                'text_preview': (text or '')[:120],
                'exception_detail': '',
            }
            log_event('runtime.warmup_renderer_finished', stage='warmup', **payload)
            return payload
        except Exception as exc:
            exception_detail = f'{type(exc).__name__}: {exc}'
            log_event(
                'runtime.warmup_renderer_retry',
                stage='warmup',
                attempt_count=attempt_count,
                exception_detail=exception_detail,
            )
            if now_fn() >= deadline:
                payload = {
                    'status': 'failed',
                    'attempt_count': attempt_count,
                    'text_preview': '',
                    'exception_detail': exception_detail,
                }
                log_event('runtime.warmup_renderer_failed', stage='warmup', **payload)
                return payload
            sleep_fn(max(retry_interval, 0.0))


def warm_runtime(*, timeout_seconds: float = 45.0, retry_interval: float = 2.0) -> dict[str, Any]:
    started = time.monotonic()
    log_event(
        'runtime.warmup_started',
        stage='warmup',
        timeout_seconds=timeout_seconds,
        retry_interval=retry_interval,
    )
    local = warm_local_clarification()
    renderer = warm_renderer_path(
        timeout_seconds=timeout_seconds,
        retry_interval=retry_interval,
    )
    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    overall_status = 'ok' if renderer.get('status') in {'ok', 'not_available'} else 'degraded'
    payload = {
        'status': overall_status,
        'elapsed_ms': elapsed_ms,
        'local': local,
        'renderer': renderer,
    }
    log_event('runtime.warmup_finished', stage='warmup', **payload)
    return payload
