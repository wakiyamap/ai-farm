#!/usr/bin/env bash
# Phase 4e: fixes from reading the first earner session.
#  - relay: trace/debug methods go to Alchemy first; unsupported-method errors fall through
#  - prompts: chains are real mainnets; session clock; bot log location
#  - earner: umask 0002 (reviewers can read manifests), SESSION_MAX_MIN in context
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
install -o root -g root -m 755 opt/farm/bin/rpc-relay opt/farm/bin/run-role /opt/farm/bin/
install -o root -g root -m 644 prompts/common.md /srv/farm/prompts/
install -o harness -g harness -m 644 prompts/roles/TOOLS.md /srv/farm/prompts/roles/
install -o root -g root -m 644 "etc/systemd/system/agent@earner-local.service.d/earner.conf" "/etc/systemd/system/agent@earner-local.service.d/"
chmod -R g+rX /srv/farm/ws/bots/paper 2>/dev/null || true
systemctl daemon-reload
systemctl restart rpc-relay.service
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  /opt/farm/bin/assemble-prompt "$inst"
done < /etc/farm/roles.conf
echo "Installed phase 4e. The running earner session keeps its old prompt; the next one gets the new one."
