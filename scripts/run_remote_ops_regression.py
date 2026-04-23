#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import tarfile
from pathlib import Path

sys.dont_write_bytecode = True

from _helpers import REPO_ROOT, emit_report


BUILD_HELPER = REPO_ROOT / 'scripts' / 'build-jordan-release'
DEPLOY_HELPER = REPO_ROOT / 'scripts' / 'deploy-jordan-release'
PULL_HELPER = REPO_ROOT / 'scripts' / 'pull-jordan-logs'


def _run_json(cmd: list[str]) -> dict:
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def main() -> None:
    export_helper = (REPO_ROOT / 'deploy' / 'systemd' / 'export-jordan-logs.sh').read_text(
        encoding='utf-8'
    )

    with tempfile.TemporaryDirectory() as td:
        output_dir = Path(td)
        build_payload = _run_json(
            [sys.executable, '-B', str(BUILD_HELPER), '--output-dir', str(output_dir), '--json']
        )
        archive_path = Path(build_payload.get('archive_path', ''))
        manifest = build_payload.get('manifest', {})
        top_level = ''
        archived_manifest: dict = {}
        archive_exists = archive_path.exists()
        if archive_path.exists():
            with tarfile.open(archive_path, 'r:gz') as tar:
                names = tar.getnames()
                if names:
                    top_level = names[0].split('/', 1)[0]
                manifest_member = tar.extractfile(f'{top_level}/release-manifest.json') if top_level else None
                if manifest_member is not None:
                    archived_manifest = json.loads(manifest_member.read().decode('utf-8'))

        deploy_payload = _run_json([
            sys.executable,
            '-B',
            str(DEPLOY_HELPER),
            '--remote',
            'root@example-vps',
            '--bundle',
            str(archive_path),
            '--dry-run',
            '--json',
        ])
        pull_payload = _run_json([
            sys.executable,
            '-B',
            str(PULL_HELPER),
            '--remote',
            'root@example-vps',
            '--dry-run',
            '--json',
        ])

    results = [
        {
            'name': 'build_helper_creates_release_archive',
            'pass': archive_exists,
        },
        {
            'name': 'release_manifest_contains_revision_metadata',
            'pass': bool(manifest.get('release_id'))
            and bool(manifest.get('commit_sha'))
            and bool(manifest.get('requirements_sha256'))
            and isinstance(manifest.get('expected_runtime_entrypoints'), list),
        },
        {
            'name': 'release_archive_embeds_release_manifest',
            'pass': archived_manifest.get('release_id') == manifest.get('release_id')
            and archived_manifest.get('commit_sha') == manifest.get('commit_sha'),
        },
        {
            'name': 'deploy_helper_uses_activation_backend_and_runtime_root',
            'pass': any('activate-jordan-release.sh' in ' '.join(cmd) for cmd in deploy_payload.get('commands', []))
            and '/runtime/incoming' in str(deploy_payload.get('remote_bundle', '')),
        },
        {
            'name': 'pull_helper_uses_canonical_export_destination',
            'pass': pull_payload.get('dest_dir') == str(REPO_ROOT / 'workspace' / 'logs' / 'exports')
            and '/workspace/logs/exports/jordan-logs-' in str(pull_payload.get('remote_archive', '')),
        },
        {
            'name': 'export_manifest_includes_release_revision_fields',
            'pass': 'release_revision' in export_helper
            and 'canonical_paths' in export_helper
            and 'release_manifest' in export_helper,
        },
    ]
    emit_report(results)


if __name__ == '__main__':
    main()
