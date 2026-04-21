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


def _is_non_generic_clarify(payload: dict, expected_reason: str) -> bool:
    text = (payload.get('final_user_text') or '').lower()
    meta = payload.get('decision_metadata') or {}
    banned = ('цитат', 'книг', 'тезис')
    return (
        payload.get('decision_type') == 'clarify'
        and payload.get('delivery_mode') == 'final_text'
        and payload.get('allow_model_call') is False
        and payload.get('reason_code') == expected_reason
        and meta.get('clarify_type') == 'human_problem'
        and bool(meta.get('clarify_profile'))
        and not any(token in text for token in banned)
    )


def main() -> None:
    sexual_scope_rc, sexual_scope, sexual_scope_stderr = _run_adapter(
        'ты разбираешь сексуальные проблемы?',
        'telegram:74001',
    )
    sexual_rejection_rc, sexual_rejection, sexual_rejection_stderr = _run_adapter(
        'муж не занимается со мной сексом',
        'telegram:74002',
    )
    desire_mismatch_rc, desire_mismatch, desire_mismatch_stderr = _run_adapter(
        'я хочу секса, а муж работает круглосуточно',
        'telegram:74003',
    )
    lost_rc, lost, lost_stderr = _run_adapter(
        'я потерялся',
        'telegram:74004',
    )

    results = [
        {
            'name': 'sexual_scope_routes_to_human_problem_clarify',
            'pass': sexual_scope_rc == 0 and _is_non_generic_clarify(
                sexual_scope, 'scope-sexual-problems',
            ),
        },
        {
            'name': 'sexual_rejection_routes_to_human_problem_clarify',
            'pass': sexual_rejection_rc == 0 and _is_non_generic_clarify(
                sexual_rejection, 'sexual-rejection',
            ),
        },
        {
            'name': 'desire_mismatch_routes_to_human_problem_clarify',
            'pass': desire_mismatch_rc == 0 and _is_non_generic_clarify(
                desire_mismatch, 'desire-mismatch',
            ),
        },
        {
            'name': 'lost_and_aimless_routes_to_human_problem_clarify',
            'pass': lost_rc == 0
            and lost.get('decision_type') == 'clarify'
            and lost.get('delivery_mode') == 'final_text'
            and lost.get('allow_model_call') is False
            and lost.get('reason_code') == 'lost-and-aimless'
            and (lost.get('decision_metadata') or {}).get('clarify_type') == 'human_problem',
        },
        {
            'name': 'human_problem_clarifies_use_question_narrowing_language',
            'pass': all(
                'скажи' in (payload.get('final_user_text') or '').lower()
                or 'назови' in (payload.get('final_user_text') or '').lower()
                for payload in (sexual_scope, sexual_rejection, desire_mismatch, lost)
            ),
        },
    ]

    emit_report(
        results,
        samples={
            'sexual_scope': sexual_scope,
            'sexual_rejection': sexual_rejection,
            'desire_mismatch': desire_mismatch,
            'lost_and_aimless': lost,
        },
        stderr={
            'sexual_scope': sexual_scope_stderr,
            'sexual_rejection': sexual_rejection_stderr,
            'desire_mismatch': desire_mismatch_stderr,
            'lost_and_aimless': lost_stderr,
        },
    )


if __name__ == '__main__':
    main()
