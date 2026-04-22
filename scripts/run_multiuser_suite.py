#!/usr/bin/env python3
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from _helpers import run_suite


def main() -> None:
    run_suite([
        'run_multiuser_5way_dispatch_smoke.py',
        'run_multiuser_5way_smoke.py',
        'run_multiuser_dispatch_integration_regression.py',
        'run_multiuser_dispatch_regression.py',
        'run_multiuser_isolation_regression.py',
        'run_multiuser_polish_regression.py',
    ], 'multiuser')


if __name__ == '__main__':
    main()
