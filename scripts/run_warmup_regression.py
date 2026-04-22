#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from library._core.runtime import warmup as warmup_module


def main() -> None:
    results: list[dict[str, object]] = []

    local = warmup_module.warm_local_clarification()
    results.append({
        'name': 'warm_local_clarification_returns_profile',
        'pass': local.get('status') == 'ok' and bool(local.get('clarify_profile')) and bool(local.get('text_preview')),
    })

    original_renderer = getattr(warmup_module.llm_renderer_module, '_llm_renderer', None)
    original_backend = getattr(warmup_module.llm_renderer_module, '_llm_renderer_backend', 'none')
    original_detail = getattr(warmup_module.llm_renderer_module, '_llm_renderer_backend_detail', '')
    original_autoload = warmup_module.llm_renderer_module._autoload_renderer_from_env
    warmup_module.llm_renderer_module._llm_renderer = None
    warmup_module.llm_renderer_module._llm_renderer_backend = 'none'
    warmup_module.llm_renderer_module._llm_renderer_backend_detail = ''
    warmup_module.llm_renderer_module._autoload_renderer_from_env = lambda: None
    try:
        unavailable = warmup_module.warm_renderer_path(timeout_seconds=0.01, retry_interval=0)
    finally:
        warmup_module.llm_renderer_module._llm_renderer = original_renderer
        warmup_module.llm_renderer_module._llm_renderer_backend = original_backend
        warmup_module.llm_renderer_module._llm_renderer_backend_detail = original_detail
        warmup_module.llm_renderer_module._autoload_renderer_from_env = original_autoload
    results.append({
        'name': 'warm_renderer_path_skips_when_unavailable',
        'pass': unavailable.get('status') == 'not_available' and unavailable.get('attempt_count') == 0,
    })

    attempts = {'count': 0}

    def flaky_renderer(*, request, prompt, attempt, violations):
        attempts['count'] += 1
        if attempts['count'] < 3:
            raise RuntimeError('warming up')
        return 'Привет.'

    retry = warmup_module.warm_renderer_path(
        timeout_seconds=1,
        retry_interval=0,
        render_fn=flaky_renderer,
        sleep_fn=lambda _: None,
        now_fn=(lambda values=iter([0.0, 0.1, 0.2]): lambda: next(values, 0.2))(),
    )
    results.append({
        'name': 'warm_renderer_path_retries_then_succeeds',
        'pass': retry.get('status') == 'ok' and retry.get('attempt_count') == 3 and retry.get('text_preview') == 'Привет.',
    })

    attempts = {'count': 0}

    def failing_renderer(*, request, prompt, attempt, violations):
        attempts['count'] += 1
        raise RuntimeError('gateway down')

    failed = warmup_module.warm_renderer_path(
        timeout_seconds=0,
        retry_interval=0,
        render_fn=failing_renderer,
        sleep_fn=lambda _: None,
        now_fn=lambda: 0.0,
    )
    results.append({
        'name': 'warm_renderer_path_reports_failure_detail',
        'pass': failed.get('status') == 'failed'
        and failed.get('attempt_count') == 1
        and 'RuntimeError: gateway down' in str(failed.get('exception_detail', '')),
    })

    passed = sum(1 for item in results if item['pass'])
    total = len(results)
    for item in results:
        marker = 'PASS' if item['pass'] else 'FAIL'
        print(f'[{marker}] {item["name"]}')
    print(f'{passed}/{total}')

    if passed != total:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
