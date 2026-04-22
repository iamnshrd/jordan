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
    mentor_dispatch = (REPO_ROOT / 'library' / 'mentor_dispatch.py').read_text(
        encoding='utf-8'
    )
    coverage_report = (REPO_ROOT / 'scripts' / 'run_dialogue_coverage_report.py').read_text(
        encoding='utf-8'
    )
    gitignore = (REPO_ROOT / '.gitignore').read_text(encoding='utf-8')
    deploy_doc = (REPO_ROOT / 'DEPLOY_SYSTEMD.md').read_text(encoding='utf-8')
    export_helper = (REPO_ROOT / 'deploy' / 'systemd' / 'export-jordan-logs.sh').read_text(
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
        {
            'name': 'mentor_dispatch_no_longer_bootstraps_hardcoded_legacy_target',
            'pass': '_bootstrap_legacy_user' not in mentor_dispatch
            and 'LEGACY_TARGET' not in mentor_dispatch,
        },
        {
            'name': 'coverage_report_uses_canonical_audit_log_path',
            'pass': "REPO_ROOT / 'conversation_audit.jsonl'" not in coverage_report
            and 'CONVERSATION_AUDIT_LOG' in coverage_report,
        },
        {
            'name': 'gitignore_covers_root_runtime_artifacts',
            'pass': 'conversation_audit.jsonl' in gitignore
            and 'openclaw.log' in gitignore,
        },
        {
            'name': 'deploy_doc_avoids_repo_root_scp_targets',
            'pass': 'scp user@your-vps:$JORDAN_HOME/workspace/logs/conversation_audit.jsonl ./conversation_audit.jsonl' not in deploy_doc
            and 'scp user@your-vps:$JORDAN_HOME/workspace/logs/openclaw.log ./openclaw.log' not in deploy_doc
            and 'export-jordan-logs.sh' in deploy_doc,
        },
        {
            'name': 'export_helper_reconstructs_empty_audit_from_runtime_log',
            'pass': 'derived_from_runtime' in export_helper
            and 'manifest.json' in export_helper
            and 'conversation_audit_source' in export_helper,
        },
    ]
    emit_report(results)


if __name__ == '__main__':
    main()
