#!/usr/bin/env bash
# Phase 3: paper runner (bots as supervised services, no keys).
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }

apt-get install -y jq >/dev/null 2>&1 || true

install -o root -g root -m 755 opt/farm/bin/paper opt/farm/bin/paper-ctl opt/farm/bin/run-role /opt/farm/bin/
install -d -o root -g root -m 755 /opt/farm/context
install -o root -g root -m 755 opt/farm/context/earner opt/farm/context/paper-reviewer /opt/farm/context/
install -o root -g root -m 644 "etc/systemd/system/paper@.service" /etc/systemd/system/
visudo -cf etc/sudoers.d/farm-paper
install -o root -g root -m 440 etc/sudoers.d/farm-paper /etc/sudoers.d/farm-paper
install -o root -g root -m 644 prompts/common.md /srv/farm/prompts/
install -o harness -g harness -m 644 prompts/roles/*.md /srv/farm/prompts/roles/

# bots/paper: earners create bot dirs; bots/archive: written only by paper-ctl (root) -> farmgate
WS=/srv/farm/ws
chown root:farm "$WS/bots/paper"; chmod 2775 "$WS/bots/paper"
setfacl -m d:g:farm:rwX "$WS/bots/paper"
# farmbot must traverse the workspace to reach its bot directory
usermod -aG farm farmbot

systemctl daemon-reload
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  /opt/farm/bin/assemble-prompt "$inst"
done < /etc/farm/roles.conf
echo "Installed phase 3."
