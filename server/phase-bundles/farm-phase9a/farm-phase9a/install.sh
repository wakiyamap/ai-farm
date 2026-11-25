#!/usr/bin/env bash
# Phase 9a:
#  - the codex researcher instance is renamed researcher -> researcher-chatgpt (role file unchanged);
#    farm-researcher.timer is replaced by farm-researcher-chatgpt.timer (daily 04:10 JST)
#  - researcher-claude may run python3 and jq (the codex researcher already can: full shell);
#    relay/cast calls must use the literal URL (variable expansion is rejected by the claude harness)
#  - farm-dash: Recent runs show the instance (researcher-chatgpt / researcher-claude), timers list
#    every farm-*.timer
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
bash -n opt/farm/bin/run-role; python3 -I -m py_compile opt/farm/bin/farm-dash
if systemctl is-active --quiet agent@researcher.service; then
  echo "agent@researcher is running right now; re-run this after it finishes" >&2; exit 1
fi
install -o root -g root -m 755 opt/farm/bin/run-role opt/farm/bin/farm-dash /opt/farm/bin/
cp -a /etc/farm/roles.conf "/etc/farm/roles.conf.bak-$(date +%Y%m%d%H%M)"
sed -i -E 's/^researcher([[:space:]]+researcher[[:space:]]+codex[[:space:]])/researcher-chatgpt\1/' /etc/farm/roles.conf
grep -E '^researcher' /etc/farm/roles.conf
install -d -o root -g root -m 755 /srv/farm/runners/researcher-chatgpt
/opt/farm/bin/assemble-prompt researcher-chatgpt
if [[ -f /etc/systemd/system/farm-researcher.timer ]]; then
  systemctl disable --now farm-researcher.timer || true
  mv /etc/systemd/system/farm-researcher.timer "/etc/systemd/system/farm-researcher.timer.bak-9a"
fi
install -o root -g root -m 644 etc/systemd/system/farm-researcher-chatgpt.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now farm-researcher-chatgpt.timer
systemctl restart farm-dash.service
systemctl list-timers 'farm-researcher*' --no-pager
echo "Installed phase 9a."
