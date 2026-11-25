#!/usr/bin/env bash
# Phase 9b (replaces the unreleased 9a naming):
#  - the codex researcher instance is renamed researcher (or researcher-chatgpt, if 9a was applied)
#    -> researcher-codex (role file unchanged); farm-researcher[-chatgpt].timer is replaced by
#    farm-researcher-codex.timer (daily 04:10 JST)
#  - researcher-claude may run python3 and jq; relay/cast calls must use the literal URL
#  - farm-dash: Recent runs show the instance, timers list every farm-*.timer
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
bash -n opt/farm/bin/run-role; python3 -I -m py_compile opt/farm/bin/farm-dash
for old in researcher researcher-chatgpt; do
  if systemctl is-active --quiet "agent@$old.service"; then
    echo "agent@$old is running right now; re-run this after it finishes" >&2; exit 1
  fi
done
install -o root -g root -m 755 opt/farm/bin/run-role opt/farm/bin/farm-dash /opt/farm/bin/
cp -a /etc/farm/roles.conf "/etc/farm/roles.conf.bak-$(date +%Y%m%d%H%M)"
sed -i -E 's/^researcher(-chatgpt)?([[:space:]]+researcher[[:space:]]+codex[[:space:]])/researcher-codex\2/' /etc/farm/roles.conf
grep -E '^researcher' /etc/farm/roles.conf
install -d -o root -g root -m 755 /srv/farm/runners/researcher-codex
/opt/farm/bin/assemble-prompt researcher-codex
for t in farm-researcher farm-researcher-chatgpt; do
  if [[ -f "/etc/systemd/system/$t.timer" ]]; then
    systemctl disable --now "$t.timer" || true
    mv "/etc/systemd/system/$t.timer" "/etc/systemd/system/$t.timer.bak-9b"
  fi
done
install -o root -g root -m 644 etc/systemd/system/farm-researcher-codex.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now farm-researcher-codex.timer
systemctl restart farm-dash.service
systemctl list-timers 'farm-researcher*' --no-pager
echo "Installed phase 9b."
