# Systemd Deploy

This repository now writes unified structured runtime logs to one canonical file:

- `$JORDAN_HOME/workspace/logs/jordan.jsonl`
- `$JORDAN_HOME/workspace/logs/openclaw.log`

Use this file as the primary artifact when copying logs off the server for
analysis.

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
sudo chmod +x /usr/local/bin/configure-openclaw-logging
sudo chmod +x /usr/local/bin/restart-jordan-runtime
sudo systemctl daemon-reload
sudo systemctl enable --now jordan-mentor-dispatch.timer
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

Status:

```bash
systemctl status jordan-mentor-dispatch.timer
systemctl status jordan-mentor-dispatch.service
```

Restart Jordan + OpenClaw after `git pull`:

```bash
sudo /usr/local/bin/restart-jordan-runtime
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
tail -f "$JORDAN_HOME/workspace/logs/openclaw.log"
```

## SCP Workflow

Copy the single canonical log file to your local machine:

```bash
scp user@your-vps:$JORDAN_HOME/workspace/logs/jordan.jsonl ./jordan.jsonl
scp user@your-vps:$JORDAN_HOME/workspace/logs/openclaw.log ./openclaw.log
```

Then send me `jordan.jsonl`, `openclaw.log`, or the relevant fragments.
