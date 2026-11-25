#!/usr/bin/env bash
# Phase 6f: session reports can no longer be lost (inbox/human/2026-11-04-meta-session-logs.md).
#   - record-run (root, ExecStopPost): appends an outcome=no_report line for any run that left
#     none, then chattr +a on logs/sessions/*.jsonl (append works, rewrites fail)
#   - run-role: meta may run python3 tools/* and read git log/show/diff/status; every claude
#     role may run tools/session-report.py
#   - common.md: says the files are append-only and how to write the report
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/record-run
bash -n opt/farm/bin/run-role
install -o root -g root -m 755 opt/farm/bin/record-run opt/farm/bin/run-role /opt/farm/bin/
install -o root -g root -m 644 prompts/common.md /srv/farm/prompts/
WS=/srv/farm/ws
install -d -o harness -g farm -m 2775 "$WS/logs/sessions"
setfacl -m d:g:farm:rwX -m d:m::rwx "$WS/logs/sessions"
# existing files: group-writable (agents of any role append), then append-only
for f in "$WS"/logs/sessions/*.jsonl; do
  [[ -f "$f" ]] || continue
  chattr -a "$f" 2>/dev/null || true
  chmod 0664 "$f"; chgrp farm "$f"
  setfacl -m g:farm:rw "$f"
  chattr +a "$f"
done
lsattr "$WS"/logs/sessions/*.jsonl 2>/dev/null | head
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  /opt/farm/bin/assemble-prompt "$inst"
done < /etc/farm/roles.conf
# prove the append path still works for an agent user
sudo -u harness bash -c 'echo -n "" >> /srv/farm/ws/logs/sessions/$(date -u +%F).jsonl' && echo "append as harness: ok"
echo "Installed phase 6f."
