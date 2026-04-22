#!/usr/bin/env python3
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from _helpers import run_suite


def main() -> None:
    run_suite([
        'run_commitment_regression.py',
        'run_mentor_effectiveness_regression.py',
        'run_mentor_outcome_regression.py',
        'run_mentor_plan_regression.py',
        'run_mentor_profile_regression.py',
        'run_mentor_regression.py',
    ], 'mentor')


if __name__ == '__main__':
    main()
