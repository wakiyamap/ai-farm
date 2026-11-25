#!/usr/bin/env bash
# Phase 6q:
#   - record-run: a run that wrote no report but left scratch/report-<run_id>.json gets that draft
#     appended (marked harness-recovered) instead of a bare no_report line (meta proposal 11-06 §1)
#   - farm-dash: the review column reads the newest decision (fix / promote / ... and "(unchanged)")
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/farm-dash opt/farm/bin/record-run
install -o root -g root -m 755 opt/farm/bin/farm-dash opt/farm/bin/record-run /opt/farm/bin/
systemctl restart farm-dash.service
sleep 1
curl -sf -m 10 http://127.0.0.1:8090/brief.txt | sed -n '/## Paper bots/,/^$/p'
echo "Installed phase 6q."
