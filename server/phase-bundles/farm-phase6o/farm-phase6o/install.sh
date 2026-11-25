#!/usr/bin/env bash
# Phase 6o: things that must come back after a reboot, and the earner's empty-turn exits.
#   - agent@earner-local: enabled at boot, waits for the LLM on :8003 first
#   - paper@ / bot@: [Install] drop-ins; paper-ctl start/stop/archive and gate promote/stop
#     enable/disable the unit, so running bots return after a reboot
#   - run-role (dsh): when the model ends its turn with no tool call and no report, dsh is
#     started again in the same run (max 3 attempts, >=10 min left) instead of losing the session
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
bash -n opt/farm/bin/run-role
python3 -I -m py_compile opt/farm/bin/paper-ctl opt/farm/bin/gate-ctl
visudo -cf etc/sudoers.d/farm-gate
install -o root -g root -m 755 opt/farm/bin/run-role opt/farm/bin/paper-ctl opt/farm/bin/gate-ctl /opt/farm/bin/
install -o root -g root -m 440 etc/sudoers.d/farm-gate /etc/sudoers.d/farm-gate
install -d -o root -g root -m 755 /etc/systemd/system/paper@.service.d /etc/systemd/system/bot@.service.d /etc/systemd/system/agent@earner-local.service.d
install -o root -g root -m 644 etc/systemd/system/paper@.service.d/install.conf /etc/systemd/system/paper@.service.d/
install -o root -g root -m 644 etc/systemd/system/bot@.service.d/install.conf /etc/systemd/system/bot@.service.d/
install -o root -g root -m 644 etc/systemd/system/agent@earner-local.service.d/boot.conf /etc/systemd/system/agent@earner-local.service.d/
systemctl daemon-reload
systemctl enable agent@earner-local.service
# enable (without touching) every paper/live bot that is running now
for u in $(systemctl list-units --plain --no-legend --state=active 'paper@*.service' 'bot@*.service' | awk '{print $1}'); do
  systemctl enable "$u"
done
systemctl is-enabled agent@earner-local.service
systemctl list-unit-files 'paper@*' 'bot@*' --no-legend | head -20
echo "Installed phase 6o. The running earner session keeps the old run-role until its next restart."
