#!/usr/bin/env bash
# Phase 6s: paper-ctl start/restart clear a start-limit failure first and report the unit's real
# state instead of "ok" (inbox/human/2026-11-06-meta-paper-start-limit.md).
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/paper-ctl
install -o root -g root -m 755 opt/farm/bin/paper-ctl /opt/farm/bin/
sudo -u harness /opt/farm/bin/paper list
echo "Installed phase 6s."
