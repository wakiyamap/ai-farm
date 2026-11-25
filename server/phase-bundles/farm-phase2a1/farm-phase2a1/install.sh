#!/usr/bin/env bash
# Phase 2a.1: let agents actually use kb / wiki.
#  - earner: turn off dsh's internal sandbox (it blocks sudo and the network)
#  - Claude roles: one command per call, drafts in scratch/
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }

install -o root -g root -m 755 opt/farm/bin/run-role /opt/farm/bin/
install -o root -g root -m 644 \
  "etc/systemd/system/agent@earner-local.service.d/earner.conf" \
  "/etc/systemd/system/agent@earner-local.service.d/"

install -o root -g root -m 644 prompts/common.md /srv/farm/prompts/
install -o harness -g harness -m 644 prompts/roles/TOOLS.md /srv/farm/prompts/roles/

# Shared drafts directory; inherits the workspace's group-write ACL
install -d -o root -g farm -m 2775 /srv/farm/ws/scratch

systemctl daemon-reload
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  /opt/farm/bin/assemble-prompt "$inst"
done < /etc/farm/roles.conf

systemctl show -p Environment agent@earner-local.service | tr ' ' '\n' | grep DSH_PERMISSION_MODE
echo "Installed phase 2a.1."
