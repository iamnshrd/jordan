# Systemd Deploy

This repository now writes unified structured runtime logs to one canonical file:

- `/opt/jordan/workspace/logs/jordan.jsonl`

Use this file as the primary artifact when copying logs off the server for
analysis.

## Assumptions

- repo is deployed at `/opt/jordan`
- Python virtualenv lives at `/opt/jordan/.venv`
- OpenClaw is configured separately
- Jordan mentor dispatch should run every 15 minutes

## Install

Copy the repo to the server and prepare the environment:

```bash
cd /opt/jordan
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python3 -m library kb build
python3 -m library kb doctor
chmod +x deploy/systemd/run-mentor-dispatch.sh
sudo mkdir -p /opt/jordan/workspace/logs
```

Install the unit files:

```bash
sudo cp deploy/systemd/jordan-mentor-dispatch.service /etc/systemd/system/
sudo cp deploy/systemd/jordan-mentor-dispatch.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now jordan-mentor-dispatch.timer
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
tail -f /opt/jordan/workspace/logs/jordan.jsonl
```

## SCP Workflow

Copy the single canonical log file to your local machine:

```bash
scp user@your-vps:/opt/jordan/workspace/logs/jordan.jsonl ./jordan.jsonl
```

Then send me `jordan.jsonl` or paste the relevant fragment.
