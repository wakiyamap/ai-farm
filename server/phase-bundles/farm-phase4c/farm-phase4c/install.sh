#!/usr/bin/env bash
# Phase 4c: live bots may connect to the signer socket (group farmbot).
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
install -o root -g root -m 644 "etc/systemd/system/bot@.service" /etc/systemd/system/
systemctl daemon-reload
ls -l /run/farm/signer.sock
echo "Installed phase 4c."
