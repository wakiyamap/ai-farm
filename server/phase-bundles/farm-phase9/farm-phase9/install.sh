#!/usr/bin/env bash
# Phase 9: a second researcher instance on Claude (opus) next to the codex researcher.
#   roles.conf: researcher-claude  researcher  claude  opus   (same role file, own runner dir)
#   run-role:   claude permission set for the researcher role
#   timer:      farm-researcher-claude.timer, daily 16:10 JST (codex researcher ~04:00 JST)
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
bash -n opt/farm/bin/run-role
install -o root -g root -m 755 opt/farm/bin/run-role /opt/farm/bin/
if ! grep -qE '^researcher-claude[[:space:]]' /etc/farm/roles.conf; then
  cp -a /etc/farm/roles.conf "/etc/farm/roles.conf.bak-$(date +%Y%m%d%H%M)"
  printf 'researcher-claude\tresearcher\tclaude\topus\n' >> /etc/farm/roles.conf
fi
grep -E '^researcher' /etc/farm/roles.conf
install -d -o root -g root -m 755 /srv/farm/runners/researcher-claude
/opt/farm/bin/assemble-prompt researcher-claude
ls -la /srv/farm/runners/researcher-claude
install -o root -g root -m 644 etc/systemd/system/farm-researcher-claude.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now farm-researcher-claude.timer
systemctl list-timers 'farm-researcher*' --no-pager
echo "Installed phase 9. First run: sudo systemctl start agent@researcher-claude  (or wait for 16:10 JST)"
