#!/usr/bin/env bash
# Phase 6v: farm-dash ignores subdirectories (inbox/*/done/) when listing inboxes.
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/farm-dash
install -o root -g root -m 755 opt/farm/bin/farm-dash /opt/farm/bin/
systemctl restart farm-dash.service
echo "Installed phase 6v."
