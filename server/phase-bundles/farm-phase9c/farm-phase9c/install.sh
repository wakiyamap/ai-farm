#!/usr/bin/env bash
# Phase 9c: farm-dash lists every installed farm-*.timer (researcher-codex / researcher-claude were
# hidden behind a hard-coded name list) instead of a fixed set.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/farm-dash
install -o root -g root -m 755 opt/farm/bin/farm-dash /opt/farm/bin/
systemctl restart farm-dash.service
echo "Installed phase 9c."
