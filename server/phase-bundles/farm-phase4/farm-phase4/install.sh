#!/usr/bin/env bash
# Phase 4: money. signer (keys + policy), gate (promote/fund/sweep/stop), watchdog.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }

# signing deps, system-wide (farmgate runs python3 -I, so no user site-packages)
apt-get install -y python3-coincurve python3-rlp python3-pycryptodome >/dev/null 2>&1 || {
  echo "apt packages missing; installing with pip into /opt/farm/pylib"
  install -d -o root -g root -m 755 /opt/farm/pylib
  pip install --quiet --target /opt/farm/pylib coincurve rlp pycryptodome
}
python3 -I -c "import sys; sys.path.insert(0, '/opt/farm/pylib'); import coincurve, rlp, Crypto" \
  || { echo "signing libraries not importable" >&2; exit 1; }

install -d -o root -g root -m 755 /opt/farm/lib
install -o root -g root -m 644 opt/farm/lib/farmkeys.py opt/farm/lib/farmbot_signer.py opt/farm/lib/bip39-english.txt /opt/farm/lib/
echo "2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda  /opt/farm/lib/bip39-english.txt" | sha256sum -c - >/dev/null
install -o root -g root -m 755 opt/farm/bin/farm-signer opt/farm/bin/farm-watchdog opt/farm/bin/gate opt/farm/bin/gate-ctl opt/farm/bin/gate-root /opt/farm/bin/
install -o root -g root -m 644 etc/farm/gate.json /etc/farm/
install -o root -g root -m 644 "etc/systemd/system/bot@.service" etc/systemd/system/farm-signer.service etc/systemd/system/farm-watchdog.service /etc/systemd/system/
visudo -cf etc/sudoers.d/farm-gate
install -o root -g root -m 440 etc/sudoers.d/farm-gate /etc/sudoers.d/farm-gate
install -o harness -g harness -m 644 prompts/roles/*.md /srv/farm/prompts/roles/ 2>/dev/null || true

# farmgate state and the master key (generated once, never printed)
install -d -o farmgate -g farmgate -m 700 /var/lib/farmgate
if [[ ! -s /var/lib/farmgate/mnemonic ]]; then
  (umask 077; python3 -I -c "
import sys, os; sys.path[:0]=['/opt/farm/pylib','/opt/farm/lib']
import farmkeys; print(farmkeys.entropy_to_mnemonic(os.urandom(32)))" > /var/lib/farmgate/mnemonic)
  chown farmgate:farmgate /var/lib/farmgate/mnemonic
  chmod 400 /var/lib/farmgate/mnemonic
  echo "NEW 24-word mnemonic generated at /var/lib/farmgate/mnemonic -- write it down offline (see README)"
fi
rm -f /var/lib/farmgate/master.key
# farmgate needs the workspace group to read live manifests and write inbox/live
usermod -aG farm farmgate
usermod -aG farmbot farmgate 2>/dev/null || true
WS=/srv/farm/ws
chown farmgate:farm "$WS/bots/live"; chmod 2755 "$WS/bots/live"

systemctl daemon-reload
systemctl enable --now farm-signer.service farm-watchdog.service
sleep 2
systemctl --no-pager --lines=2 status farm-signer.service farm-watchdog.service || true
echo
echo "Intermediate wallet (deposit ETH for gas here, a little on each chain first):"
sudo -u farmgate /opt/farm/bin/gate-ctl intermediate
echo "Installed phase 4."
