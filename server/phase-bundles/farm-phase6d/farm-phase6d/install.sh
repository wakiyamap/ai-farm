#!/usr/bin/env bash
# Phase 6d: dashboard "Copy for Claude" button + /brief.txt, timer next/last fix,
# and farm-acl-fix.timer (opens group read on files agents create 0600).
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/farm-dash
bash -n opt/farm/bin/farm-acl-fix
install -o root -g root -m 755 opt/farm/bin/farm-dash opt/farm/bin/farm-acl-fix /opt/farm/bin/
install -o root -g root -m 644 etc/systemd/system/farm-acl-fix.service etc/systemd/system/farm-acl-fix.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now farm-acl-fix.timer
systemctl start farm-acl-fix.service
systemctl restart farm-dash.service
sleep 1
curl -sf -m 10 http://127.0.0.1:8090/brief.txt | head -3
echo "Installed phase 6d."
