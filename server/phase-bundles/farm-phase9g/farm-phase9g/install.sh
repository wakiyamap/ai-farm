#!/usr/bin/env bash
# Phase 9g = 9f + the watchdog false alarm of 2026-11-09 17:44Z:
#  - the executor deployment is a bot-key tx sent by the gate, not the signer; the watchdog saw the
#    bot nonce advance with no signer record and halted everything as a possible key compromise.
#    gate-ctl now logs deploy_executor_sent (with nonce) right after broadcasting, and sweep /
#    sweep_usdc with their nonce; the watchdog accepts those gate.log records as known nonces.
#  - farm-watchdog runs with NoNewPrivileges=no so its emergency `gate-ctl stop` can archive bots
#    through sudo (the stop was partial: "archive failed: no new privileges").
# Does NOT clear the halt; see the reply for the recovery steps.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/gate-ctl opt/farm/bin/farm-signer opt/farm/bin/ledger-ingest opt/farm/bin/farm-watchdog
for f in gate-ctl farm-signer ledger-ingest farm-watchdog; do cp -a "/opt/farm/bin/$f" "/opt/farm/bin/.$f.bak-9g"; done
install -o root -g root -m 755 opt/farm/bin/gate-ctl opt/farm/bin/farm-signer opt/farm/bin/ledger-ingest opt/farm/bin/farm-watchdog /opt/farm/bin/
install -d -m 755 /etc/systemd/system/farm-watchdog.service.d
install -o root -g root -m 644 etc/systemd/system/farm-watchdog.service.d/sudo.conf /etc/systemd/system/farm-watchdog.service.d/
systemctl daemon-reload
systemctl restart farm-signer.service farm-watchdog.service
sleep 3
systemctl is-active farm-signer.service farm-watchdog.service
echo "halt flag: $( [[ -e /var/lib/farmgate/halt ]] && echo present || echo absent )"
echo "Installed phase 9g."
