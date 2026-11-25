#!/usr/bin/env bash
# Phase 6g: meta every 6 h instead of 12 h while the process is still being shaped.
# Revert: change OnUnitInactiveSec back to 12h and re-run.
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
install -o root -g root -m 644 etc/systemd/system/farm-meta.timer /etc/systemd/system/
systemctl daemon-reload
systemctl restart farm-meta.timer
systemctl list-timers farm-meta.timer --no-pager
echo "Installed phase 6g."
