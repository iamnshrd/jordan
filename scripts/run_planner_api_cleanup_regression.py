#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from _helpers import REPO_ROOT, emit_report


ALLOWED_IMPORT_FILES = {
    'library/_core/runtime/orchestrator.py',
    'library/_core/runtime/planner.py',
}


def main() -> None:
    offenders: list[str] = []
    for path in (REPO_ROOT / 'library').rglob('*.py'):
        rel = path.relative_to(REPO_ROOT).as_posix()
        text = path.read_text(encoding='utf-8')
        if 'build_answer_plan' not in text:
            continue
        if rel in ALLOWED_IMPORT_FILES:
            continue
        offenders.append(rel)

    results = [
        {
            'name': 'build_answer_plan_is_not_used_outside_orchestrator_and_planner',
            'pass': not offenders,
        },
    ]
    emit_report(results, samples={'offenders': offenders})


if __name__ == '__main__':
    main()
