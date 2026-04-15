#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from library.config import WORKSPACE
from library.mentor_targets_admin import normalize_targets, onboarding_report, legacy_default_report, upsert_target


def main() -> None:
    results = []
    with tempfile.TemporaryDirectory() as td:
        # basic policy expectations from pure functions/state shape
        data = upsert_target('telegram:111', target='111', enabled=False, auto_onboard='manual-review')
        data = normalize_targets()
        users = data.get('users', [])
        results.append({
            'name': 'manual_review_default_policy_present',
            'pass': any(x.get('user_id') == 'telegram:111' and x.get('auto_onboard') == 'manual-review' for x in users),
        })

        report = onboarding_report()
        results.append({
            'name': 'onboarding_report_has_counts',
            'pass': 'total_users' in report and 'enabled_users' in report,
        })

        legacy = legacy_default_report()
        results.append({
            'name': 'legacy_report_returns_shape',
            'pass': 'legacy_default_files' in legacy and 'count' in legacy,
        })

    total = len(results)
    passed = sum(1 for x in results if x.get('pass'))
    print(json.dumps({'total': total, 'pass': passed, 'results': results}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if total == passed else 1)


if __name__ == '__main__':
    main()
