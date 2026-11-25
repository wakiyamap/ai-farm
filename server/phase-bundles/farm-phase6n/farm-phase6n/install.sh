#!/usr/bin/env bash
# Phase 6n: meta proposal 2026-11-05 (run eaf9b2e0).
#   - kb query --json: untruncated rows (kb query keeps the 400-char cut)
#   - record-run: a no_report line now carries the last error-looking journal lines of the run
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/kb opt/farm/bin/record-run
install -o root -g root -m 755 opt/farm/bin/kb opt/farm/bin/record-run /opt/farm/bin/
sudo -u harness /opt/farm/bin/kb query --json "SELECT 1 AS ok" | grep -q '"ok": 1' && echo "kb --json: ok"
echo "Installed phase 6n."
