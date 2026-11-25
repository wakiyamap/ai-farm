#!/usr/bin/env bash
# Phase 2b: RPC relay + Claude auto-memory off.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }

id farmrelay >/dev/null 2>&1 || useradd --system -s /usr/sbin/nologin -d /nonexistent -M farmrelay

install -o root -g root -m 755 opt/farm/bin/rpc-relay opt/farm/bin/run-role /opt/farm/bin/
install -o root -g root -m 644 etc/farm/relay.json etc/farm/farm.nft etc/farm/claude-settings.json /etc/farm/
install -o root -g root -m 644 etc/systemd/system/rpc-relay.service /etc/systemd/system/
install -o harness -g harness -m 644 prompts/roles/TOOLS.md /srv/farm/prompts/roles/

# farm.env: add RPC_RELAY_URL without touching the paths the human set
grep -q '^RPC_RELAY_URL=' /etc/farm/farm.env || echo 'RPC_RELAY_URL=http://127.0.0.1:8545' >> /etc/farm/farm.env

# Alchemy key file: created empty if missing; the human fills it (see README)
if [[ ! -e /etc/farm/alchemy.key ]]; then
  install -o root -g farmrelay -m 640 /dev/null /etc/farm/alchemy.key
fi
chown root:farmrelay /etc/farm/alchemy.key && chmod 640 /etc/farm/alchemy.key

# ops.db must be writable by the relay (record-run runs as root and created it)
touch /var/lib/farm/ops.db
chown root:farmrelay /var/lib/farm /var/lib/farm/ops.db
chmod 775 /var/lib/farm
chmod 664 /var/lib/farm/ops.db
for f in /var/lib/farm/ops.db-wal /var/lib/farm/ops.db-shm; do
  [[ -e "$f" ]] && chown root:farmrelay "$f" && chmod 664 "$f" || true
done

systemctl daemon-reload
systemctl restart farm-nft.service
systemctl enable --now rpc-relay.service
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  /opt/farm/bin/assemble-prompt "$inst"
done < /etc/farm/roles.conf

sleep 1
systemctl --no-pager --lines=3 status rpc-relay.service || true
echo "Installed phase 2b. Put the Alchemy key in /etc/farm/alchemy.key, then: systemctl restart rpc-relay"
