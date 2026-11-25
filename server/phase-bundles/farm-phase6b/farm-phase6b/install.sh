#!/usr/bin/env bash
# Phase 6b: fork CLI waits for receipts (fixes 'NoneType has no attribute get' in replay/send/deploy);
# common.md lets paper-reviewer write security findings to inbox/human;
# run-role grants the paper-reviewer role its write set when run under the claude harness.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/fork
bash -n opt/farm/bin/run-role
install -o root -g root -m 755 opt/farm/bin/fork opt/farm/bin/run-role /opt/farm/bin/
install -o root -g root -m 644 prompts/common.md /srv/farm/prompts/
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  /opt/farm/bin/assemble-prompt "$inst"
done < /etc/farm/roles.conf
sudo -u earner /opt/farm/bin/fork status
echo "Installed phase 6b."
