#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from _helpers import REPO_ROOT, emit_report


def main() -> None:
    mentor_render = (REPO_ROOT / 'library' / '_core' / 'mentor' / 'render.py').read_text(
        encoding='utf-8'
    )
    cli_text = (REPO_ROOT / 'library' / '__main__.py').read_text(encoding='utf-8')
    targets_admin = (REPO_ROOT / 'library' / 'mentor_targets_admin.py').read_text(
        encoding='utf-8'
    )

    results = [
        {
            'name': 'unsafe_allow_prompt_removed_from_mentor_render',
            'pass': 'unsafe_allow_prompt' not in mentor_render,
        },
        {
            'name': 'legacy_report_removed_from_cli',
            'pass': 'legacy-report' not in cli_text and 'legacy_default_report' not in cli_text,
        },
        {
            'name': 'legacy_default_report_removed_from_admin_helper',
            'pass': 'def legacy_default_report' not in targets_admin,
        },
    ]
    emit_report(results)


if __name__ == '__main__':
    main()
