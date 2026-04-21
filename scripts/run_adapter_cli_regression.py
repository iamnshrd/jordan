#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys

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
    blocked_q = (
        'я не могу определиться, какой бренд трусиков лучше.. '
        'Викториас сикрет или Чебоксарский трикотаж?'
    )
    answer_q = 'Я потерял смысл, дисциплину и направление'

    blocked_rc, blocked, blocked_stderr = _run_adapter(blocked_q, 'telegram:73001')
    answer_rc, answer, answer_stderr = _run_adapter(answer_q, 'telegram:73002')

    results = [
        {
            'name': 'blocked_adapter_returns_machine_readable_contract',
            'pass': blocked_rc == 0
            and blocked.get('decision_type') in {'respond_policy_text', 'clarify', 'deny'}
            and blocked.get('delivery_mode') == 'final_text'
            and blocked.get('allow_model_call') is False
            and bool(blocked.get('final_user_text'))
            and isinstance(blocked.get('trace_id'), str),
        },
        {
            'name': 'blocked_adapter_omits_model_prompt',
            'pass': blocked_rc == 0
            and 'model_prompt' not in blocked,
        },
        {
            'name': 'respond_kb_adapter_exposes_model_prompt',
            'pass': answer_rc == 0
            and answer.get('decision_type') == 'respond_kb'
            and answer.get('delivery_mode') == 'model'
            and answer.get('allow_model_call') is True
            and isinstance(answer.get('model_prompt'), dict)
            and bool((answer.get('model_prompt') or {}).get('system')),
        },
        {
            'name': 'adapter_contract_keeps_assistant_metadata',
            'pass': blocked.get('assistant_id') == 'jordan'
            and blocked.get('knowledge_set_id') == 'jordan-kb'
            and answer.get('assistant_id') == 'jordan'
            and answer.get('knowledge_set_id') == 'jordan-kb',
        },
    ]

    emit_report(
        results,
        samples={
            'blocked': blocked,
            'answer': answer,
        },
        stderr={
            'blocked': blocked_stderr,
            'answer': answer_stderr,
        },
    )


if __name__ == '__main__':
    main()
