#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from _helpers import REPO_ROOT


ALWAYS_RUN = [
    'run_legacy_cleanup_regression.py',
    'run_default_workspace_audit_regression.py',
    'run_default_workspace_migration_regression.py',
    'run_diagnostics_boundary_regression.py',
    'run_planner_api_cleanup_regression.py',
    'run_guardrail_suite.py',
]

RUNTIME_EXTRA = [
    'run_dialogue_frame_regression.py',
    'run_dialogue_frame_update_regression.py',
    'run_unified_logging_regression.py',
]

MENTOR_EXTRA = [
    'run_mentor_suite.py',
]

PROHIBITED_ROOT_ARTIFACTS = (
    'conversation_audit.jsonl',
    'openclaw.log',
    'openclaw_telegram_audit.patch',
    'openclaw_telegram_audit_plan.md',
)

CANONICAL_RUNTIME_LOG = REPO_ROOT / 'workspace' / 'logs' / 'jordan.jsonl'
CANONICAL_AUDIT_LOG = REPO_ROOT / 'workspace' / 'logs' / 'conversation_audit.jsonl'


def _parse_git_status(stdout: str) -> list[dict]:
    rows: list[dict] = []
    for raw in stdout.splitlines():
        line = raw.rstrip('\n')
        if not line.strip():
            continue
        status = line[:2]
        path = line[3:].strip() if len(line) >= 4 else ''
        rows.append({
            'status': status,
            'path': path,
            'raw': line,
        })
    return rows


def _git_status_entries() -> list[dict]:
    proc = subprocess.run(
        ['git', '-C', str(REPO_ROOT), 'status', '--short'],
        capture_output=True,
        text=True,
    )
    return _parse_git_status(proc.stdout)


def _find_artifact_violations() -> list[str]:
    violations: list[str] = []
    for rel in PROHIBITED_ROOT_ARTIFACTS:
        if (REPO_ROOT / rel).exists():
            violations.append(rel)
    for path in sorted(REPO_ROOT.rglob('__pycache__')):
        if path.is_dir():
            violations.append(str(path.relative_to(REPO_ROOT)))
    return violations


def _run_python_check(script_name: str) -> dict:
    path = REPO_ROOT / 'scripts' / script_name
    env = dict(**__import__('os').environ)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    proc = subprocess.run(
        [sys.executable, '-B', str(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    return {
        'name': script_name,
        'kind': 'script',
        'pass': proc.returncode == 0,
        'returncode': proc.returncode,
        'reported_pass': payload.get('pass'),
        'reported_total': payload.get('total'),
        'stderr': proc.stderr.strip(),
    }


def _run_shell_syntax_check(paths: list[Path]) -> dict:
    proc = subprocess.run(
        ['bash', '-n', *[str(path) for path in paths]],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return {
        'name': 'deploy_systemd_shell_syntax',
        'kind': 'shell',
        'pass': proc.returncode == 0,
        'returncode': proc.returncode,
        'stderr': proc.stderr.strip(),
        'targets': [str(path.relative_to(REPO_ROOT)) for path in paths],
    }


def _check_log_path_policy() -> dict:
    env = dict(**__import__('os').environ)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    proc = subprocess.run(
        [sys.executable, '-B', '-m', 'library', 'state', 'log-paths'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    payload: dict = {}
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    runtime_log = Path(payload.get('runtime_log', '')) if payload.get('runtime_log') else None
    audit_log = Path(payload.get('conversation_audit_log', '')) if payload.get('conversation_audit_log') else None
    passed = (
        proc.returncode == 0
        and runtime_log == CANONICAL_RUNTIME_LOG
        and audit_log == CANONICAL_AUDIT_LOG
    )
    return {
        'name': 'log_path_policy',
        'kind': 'policy',
        'pass': passed,
        'returncode': proc.returncode,
        'runtime_log': str(runtime_log) if runtime_log else '',
        'conversation_audit_log': str(audit_log) if audit_log else '',
        'stderr': proc.stderr.strip(),
    }


def _touches_runtime_control(paths: list[str]) -> bool:
    runtime_prefixes = (
        'library/_core/runtime/',
        'library/_core/kb/',
        'library/_adapters/',
    )
    runtime_exact = {
        'library/__main__.py',
        'library/config.py',
        'scripts/run_dialogue_frame_regression.py',
        'scripts/run_dialogue_frame_update_regression.py',
        'scripts/run_unified_logging_regression.py',
    }
    return any(path.startswith(runtime_prefixes) or path in runtime_exact for path in paths)


def _touches_mentor_or_systemd(paths: list[str]) -> bool:
    mentor_prefixes = (
        'library/_core/mentor/',
        'deploy/systemd/',
    )
    mentor_exact = {
        'library/mentor_dispatch.py',
        'library/mentor_targets_admin.py',
    }
    return any(path.startswith(mentor_prefixes) or path in mentor_exact for path in paths)


def _resolve_script_matrix(touched_paths: list[str]) -> tuple[list[str], bool]:
    selected = list(ALWAYS_RUN)
    include_shell_check = False
    if _touches_runtime_control(touched_paths):
        selected.extend(RUNTIME_EXTRA)
    if _touches_mentor_or_systemd(touched_paths):
        selected.extend(MENTOR_EXTRA)
        include_shell_check = any(path.startswith('deploy/systemd/') for path in touched_paths)

    ordered: list[str] = []
    seen: set[str] = set()
    for name in selected:
        if name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered, include_shell_check


def run_post_refactor_check() -> dict:
    git_entries = _git_status_entries()
    touched_paths = [row.get('path', '') for row in git_entries if row.get('path')]
    artifact_violations = _find_artifact_violations()
    selected_scripts, include_shell_check = _resolve_script_matrix(touched_paths)

    steps: list[dict] = []
    steps.append({
        'name': 'git_status',
        'kind': 'git',
        'pass': True,
        'git_dirty': bool(git_entries),
        'entries': git_entries,
    })
    steps.append({
        'name': 'artifact_hygiene',
        'kind': 'hygiene',
        'pass': not artifact_violations,
        'violations': artifact_violations,
    })
    steps.append(_check_log_path_policy())

    if include_shell_check:
        shell_targets = sorted((REPO_ROOT / 'deploy' / 'systemd').glob('*.sh'))
        if shell_targets:
            steps.append(_run_shell_syntax_check(shell_targets))

    for script_name in selected_scripts:
        steps.append(_run_python_check(script_name))

    failed_checks = [step['name'] for step in steps if not step.get('pass')]
    suggested_reruns: list[str] = []
    for step in steps:
        if step.get('pass'):
            continue
        if step.get('kind') == 'script':
            suggested_reruns.append(f'python3 scripts/{step["name"]}')
        elif step.get('name') == 'log_path_policy':
            suggested_reruns.append('python3 -m library state log-paths')
        elif step.get('name') == 'deploy_systemd_shell_syntax':
            suggested_reruns.append('bash -n deploy/systemd/*.sh')
        elif step.get('name') == 'artifact_hygiene':
            suggested_reruns.append('git status --short')
            suggested_reruns.append("find . -type d -name '__pycache__' -prune -exec rm -rf {} +")

    return {
        'status': 'ok' if not failed_checks else 'fail',
        'steps': steps,
        'git_dirty': bool(git_entries),
        'artifact_violations': artifact_violations,
        'failed_checks': failed_checks,
        'suggested_reruns': suggested_reruns,
        'selected_scripts': selected_scripts,
        'touched_paths': touched_paths,
    }


def main() -> None:
    report = run_post_refactor_check()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report.get('status') == 'ok' else 1)


if __name__ == '__main__':
    main()
