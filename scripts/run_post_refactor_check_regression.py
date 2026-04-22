#!/usr/bin/env python3
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from _helpers import emit_report
import run_post_refactor_check as postcheck


def _restore(name: str, value) -> None:
    setattr(postcheck, name, value)


def main() -> None:
    results = []

    orig_git = postcheck._git_status_entries
    orig_artifacts = postcheck._find_artifact_violations
    orig_logs = postcheck._check_log_path_policy
    orig_matrix = postcheck._resolve_script_matrix
    orig_python = postcheck._run_python_check
    orig_shell = postcheck._run_shell_syntax_check

    try:
        postcheck._git_status_entries = lambda: []
        postcheck._find_artifact_violations = lambda: []
        postcheck._check_log_path_policy = lambda: {
            'name': 'log_path_policy',
            'kind': 'policy',
            'pass': True,
            'returncode': 0,
            'runtime_log': 'workspace/logs/jordan.jsonl',
            'conversation_audit_log': 'workspace/logs/conversation_audit.jsonl',
            'stderr': '',
        }
        postcheck._resolve_script_matrix = lambda touched: (['run_fake_green.py'], False)
        postcheck._run_python_check = lambda script_name: {
            'name': script_name,
            'kind': 'script',
            'pass': True,
            'returncode': 0,
            'reported_pass': 1,
            'reported_total': 1,
            'stderr': '',
        }
        report = postcheck.run_post_refactor_check()
        results.append({
            'name': 'postcheck_passes_when_delegated_checks_are_green',
            'pass': report.get('status') == 'ok'
            and report.get('failed_checks') == []
            and report.get('artifact_violations') == [],
        })

        postcheck._find_artifact_violations = lambda: ['conversation_audit.jsonl']
        report = postcheck.run_post_refactor_check()
        results.append({
            'name': 'postcheck_fails_when_root_artifact_is_present',
            'pass': report.get('status') == 'fail'
            and 'artifact_hygiene' in (report.get('failed_checks') or [])
            and 'git status --short' in (report.get('suggested_reruns') or []),
        })

        postcheck._find_artifact_violations = lambda: []
        postcheck._run_python_check = lambda script_name: {
            'name': script_name,
            'kind': 'script',
            'pass': False,
            'returncode': 1,
            'reported_pass': 0,
            'reported_total': 1,
            'stderr': 'boom',
        }
        report = postcheck.run_post_refactor_check()
        results.append({
            'name': 'postcheck_fails_when_delegated_script_fails',
            'pass': report.get('status') == 'fail'
            and 'run_fake_green.py' in (report.get('failed_checks') or [])
            and 'python3 scripts/run_fake_green.py' in (report.get('suggested_reruns') or []),
        })

        postcheck._resolve_script_matrix = lambda touched: ([], True)
        postcheck._run_shell_syntax_check = lambda paths: {
            'name': 'deploy_systemd_shell_syntax',
            'kind': 'shell',
            'pass': False,
            'returncode': 2,
            'stderr': 'syntax error',
            'targets': ['deploy/systemd/restart-jordan-runtime.sh'],
        }
        report = postcheck.run_post_refactor_check()
        results.append({
            'name': 'postcheck_reports_shell_syntax_failures_explicitly',
            'pass': report.get('status') == 'fail'
            and 'deploy_systemd_shell_syntax' in (report.get('failed_checks') or [])
            and 'bash -n deploy/systemd/*.sh' in (report.get('suggested_reruns') or []),
        })
    finally:
        _restore('_git_status_entries', orig_git)
        _restore('_find_artifact_violations', orig_artifacts)
        _restore('_check_log_path_policy', orig_logs)
        _restore('_resolve_script_matrix', orig_matrix)
        _restore('_run_python_check', orig_python)
        _restore('_run_shell_syntax_check', orig_shell)

    emit_report(results)


if __name__ == '__main__':
    main()
