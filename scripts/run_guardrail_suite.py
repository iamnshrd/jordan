#!/usr/bin/env python3
from __future__ import annotations

from _helpers import run_suite


def main() -> None:
    run_suite([
        'run_adaptive_guardrail_regression.py',
        'run_domain_guardrail_escalation_regression.py',
        'run_domain_guardrail_regression.py',
        'run_guardrail_tone_regression.py',
    ], 'guardrail')


if __name__ == '__main__':
    main()
