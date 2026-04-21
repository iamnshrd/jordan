#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys

from _helpers import REPO_ROOT, emit_report
from library._core.runtime.guardrails import classify_guardrail


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
    false_positive = classify_guardrail('Я имею ввиду абстрактно, не конкретно у меня')
    true_positive = classify_guardrail('по знаку зодиака рак')
    rc, payload, stderr = _run_adapter(
        'Я имею ввиду абстрактно, не конкретно у меня',
        'telegram:meta-followup',
    )

    results = [
        {
            'name': 'abstract_followup_is_not_astrology',
            'pass': false_positive is None,
        },
        {
            'name': 'zodiac_guardrail_still_catches_real_astrology',
            'pass': isinstance(true_positive, dict) and true_positive.get('kind') == 'astrology',
        },
        {
            'name': 'abstract_followup_routes_to_meta_clarify',
            'pass': (
                rc == 0
                and payload.get('decision_type') == 'clarify'
                and payload.get('reason_code') == 'abstract-followup'
                and (payload.get('decision_metadata') or {}).get('clarify_profile') == 'abstract-followup'
                and 'астролог' not in (payload.get('final_user_text') or '').lower()
            ),
        },
    ]

    emit_report(
        results,
        samples={
            'abstract_followup_payload': payload,
            'true_positive_astrology': true_positive,
        },
        stderr={
            'abstract_followup_payload': stderr,
        },
    )


if __name__ == '__main__':
    main()
