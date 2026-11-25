#!/usr/bin/env bash
# Phase 6h: two bugs from phase 6d/6f.
#   - run-role: Bash() allow rules for meta (python3 tools/*, git log/show/diff/status) and
#     session-report.py carried a '//' prefix and never matched -> still denied
#   - farm-acl-fix: find's -print0 bound only to the directory branch -> 0600 files never fixed
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
bash -n opt/farm/bin/run-role opt/farm/bin/farm-acl-fix
install -o root -g root -m 755 opt/farm/bin/run-role opt/farm/bin/farm-acl-fix /opt/farm/bin/
/opt/farm/bin/farm-acl-fix
systemctl is-active farm-acl-fix.timer >/dev/null || systemctl enable --now farm-acl-fix.timer
# show what meta will be allowed (sanity)
ROLE=meta bash -c 'source <(sed -n "/^claude_tools()/,/^}/p" /opt/farm/bin/run-role); claude_tools' | tr ',' '\n' | grep -E 'python3|git' 
echo "Installed phase 6h."
