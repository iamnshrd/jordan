# Systemd Deploy

This repository now writes unified structured runtime logs to one canonical file:

- `$JORDAN_HOME/workspace/logs/jordan.jsonl`
- `$JORDAN_HOME/workspace/logs/conversation_audit.jsonl`
- `$JORDAN_HOME/workspace/logs/openclaw.log`

Use this file as the primary artifact when copying logs off the server for
analysis.

Jordan's preferred v1 operational model is now:

1. build a release bundle locally
2. upload and activate that bundle on the VPS
3. keep `systemd` as the runtime orchestrator
4. pull canonical log snapshots back locally

## Assumptions

- repo can live anywhere on disk
- `JORDAN_HOME` points to that repo path
- Python virtualenv lives at `$JORDAN_HOME/.venv`
- OpenClaw is configured separately
- OpenClaw may be installed as a user service
- Jordan mentor dispatch should run every 15 minutes

## Install

Copy the repo to the server and prepare the environment:

```bash
cd /path/to/jordan
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python3 -m library kb build
python3 -m library kb doctor
chmod +x deploy/systemd/run-mentor-dispatch.sh
sudo mkdir -p workspace/logs
```

Create an environment file that tells systemd where the repo lives:

```bash
sudo tee /etc/default/jordan >/dev/null <<'EOF'
JORDAN_HOME=/path/to/jordan
OPENCLAW_PROFILE=jordan-peterson
EOF
```

Install the unit files:

```bash
sudo cp deploy/systemd/jordan-mentor-dispatch.service /etc/systemd/system/
sudo cp deploy/systemd/jordan-mentor-dispatch.timer /etc/systemd/system/
sudo cp deploy/systemd/configure-openclaw-logging.sh /usr/local/bin/configure-openclaw-logging
sudo cp deploy/systemd/restart-jordan-runtime.sh /usr/local/bin/restart-jordan-runtime
sudo cp deploy/systemd/update-jordan-runtime.sh /usr/local/bin/update-jordan-runtime
sudo chmod +x /usr/local/bin/configure-openclaw-logging
sudo chmod +x /usr/local/bin/restart-jordan-runtime
sudo chmod +x /usr/local/bin/update-jordan-runtime
sudo systemctl daemon-reload
sudo systemctl enable --now jordan-mentor-dispatch.timer
```

Install the release-activation backend helper:

```bash
sudo cp deploy/systemd/activate-jordan-release.sh /usr/local/bin/activate-jordan-release
sudo chmod +x /usr/local/bin/activate-jordan-release
```

Point OpenClaw file logging at the shared log directory:

```bash
sudo JORDAN_HOME=/path/to/jordan OPENCLAW_PROFILE=jordan-peterson /usr/local/bin/configure-openclaw-logging
```

Run one manual dispatch immediately:

```bash
sudo systemctl start jordan-mentor-dispatch.service
```

## Operations

## Remote-Ops Workflow

Build a release locally:

```bash
python3 scripts/build-jordan-release --json
```

Deploy the newest local bundle to the VPS:

```bash
python3 scripts/deploy-jordan-release --remote root@your-vps --json
```

The activation backend extracts the bundle under:

```bash
$JORDAN_HOME/runtime/releases/<release-id>
```

and moves the stable runtime pointer to:

```bash
$JORDAN_HOME/runtime/current
```

Current `systemd` helpers automatically prefer `runtime/current` when it exists,
so existing service names do not need to change.

Status:

```bash
systemctl status jordan-mentor-dispatch.timer
systemctl status jordan-mentor-dispatch.service
```

Restart Jordan + OpenClaw after `git pull`:

```bash
sudo /usr/local/bin/restart-jordan-runtime
```

Pull latest code, clear fresh logs, and restart everything in one step:

```bash
/usr/local/bin/update-jordan-runtime
```

That helper is still supported for repo-based updates, but it is no longer the
preferred path once release-bundle deploy is in place.

If OpenClaw is installed as a user service, prefer running the helper without
`sudo` so it can reach the user bus cleanly:

```bash
/usr/local/bin/restart-jordan-runtime
```

The one-shot update helper also prefers running without `sudo`:

```bash
/usr/local/bin/update-jordan-runtime
```

If your OpenClaw gateway is installed as a user service, the helper also tries
to restart:

```bash
systemctl --user restart openclaw-gateway-jordan-peterson.service
```

Recent journal output:

```bash
journalctl -u jordan-mentor-dispatch.service -n 100 --no-pager
```

Unified runtime log path from CLI:

```bash
python3 -m library state log-paths
```

Tail the canonical log file:

```bash
tail -f "$JORDAN_HOME/workspace/logs/jordan.jsonl"
tail -f "$JORDAN_HOME/workspace/logs/conversation_audit.jsonl"
tail -f "$JORDAN_HOME/workspace/logs/openclaw.log"
```

## Export Workflow

Do not copy logs into the repo root with commands like `scp ... ./conversation_audit.jsonl`.
That creates a second misleading copy next to the code and makes it easy to analyze stale local files
instead of the canonical runtime logs under `workspace/logs/`.

On the VPS, bundle the canonical logs first:

```bash
JORDAN_HOME=/root/jordan /root/jordan/deploy/systemd/export-jordan-logs.sh
```

From the local machine, prefer the canonical pull helper instead:

```bash
python3 scripts/pull-jordan-logs --remote root@your-vps --json
```

This writes a timestamped archive under:

```bash
$JORDAN_HOME/workspace/logs/exports/jordan-logs-<timestamp>.tar.gz
```

Each exported directory now also contains:

- `manifest.json`
- `conversation_audit.jsonl`

If the live `workspace/logs/conversation_audit.jsonl` is empty, the export helper
reconstructs the exported audit file from `workspace/logs/jordan.jsonl` by
filtering `conversation.*` and delivery-related events. That makes the archive
internally consistent even when the standalone audit file was cleared before
export.

The export manifest also records:

- release revision / commit SHA
- release id when a release bundle is active
- canonical source paths for each log file
- file sizes and mtimes
- `conversation_audit_source`

Then copy that archive somewhere outside the repo root on your local machine:

```bash
scp user@your-vps:$JORDAN_HOME/workspace/logs/exports/jordan-logs-<timestamp>.tar.gz ~/Downloads/
```

If you need a single file instead of the archive, still copy it outside the repo root:

```bash
scp user@your-vps:$JORDAN_HOME/workspace/logs/conversation_audit.jsonl ~/Downloads/jordan-conversation_audit.jsonl
scp user@your-vps:$JORDAN_HOME/workspace/logs/jordan.jsonl ~/Downloads/jordan-runtime.jsonl
scp user@your-vps:$JORDAN_HOME/workspace/logs/openclaw.log ~/Downloads/jordan-openclaw.log
```

Then send me the extracted file or the relevant fragments.
