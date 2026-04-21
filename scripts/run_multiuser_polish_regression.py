#!/usr/bin/env python3
from __future__ import annotations

from _helpers import emit_report
from library.mentor_targets_admin import normalize_targets, onboarding_report, upsert_target


def main() -> None:
    results = []
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

    results.append({
        'name': 'targets_report_still_available_after_cleanup',
        'pass': 'manual_review_users' in report and 'users_with_state' in report,
    })

    emit_report(results)


if __name__ == '__main__':
    main()
