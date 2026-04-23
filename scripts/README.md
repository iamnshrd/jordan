## Scripts

This directory holds ad-hoc regression and smoke scripts that operate on the
`library` package but are not part of the package itself.

Keep reusable runtime code in `library/`.
Keep one-off checks, experiments, and operator-facing regression entrypoints in
`scripts/`.

Operator-facing remote-ops helpers also live here:

```bash
python3 scripts/build-jordan-release --json
python3 scripts/deploy-jordan-release --remote root@your-vps --json
python3 scripts/pull-jordan-logs --remote root@your-vps --json
```

## Post-Refactor Check

Use the canonical one-shot local gate after refactors:

```bash
python3 scripts/run_post_refactor_check.py
```

Manual breakdown when it fails:

```bash
git status --short
python3 scripts/run_post_refactor_check.py
```

Then rerun the specific failing command shown in `suggested_reruns` from the
JSON report.
