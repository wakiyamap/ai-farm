#!/usr/bin/env bash
# Phase 2c: event ledger (seed sources + agent-added sources).
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }

install -o root -g root -m 755 opt/farm/bin/ledger-ingest opt/farm/bin/ledger opt/farm/bin/run-role /opt/farm/bin/
install -o root -g root -m 644 etc/farm/ledger.json etc/farm/ledger-sources.json /etc/farm/
install -o root -g root -m 644 etc/systemd/system/ledger-ingest.service etc/systemd/system/ledger-ingest.timer /etc/systemd/system/
install -o harness -g harness -m 644 prompts/roles/*.md /srv/farm/prompts/roles/

# Ledger dir: daemon (farmdata) writes the db; agents (group farm) may add sources
WS=/srv/farm/ws
setfacl -bR "$WS/ledger"
chown farmdata:farm "$WS/ledger"
chmod 2755 "$WS/ledger"
install -d -o farmdata -g farm -m 2775 "$WS/ledger/sources.d"
setfacl -m d:g:farm:rwX "$WS/ledger/sources.d"

# Python keccak for topic validation (ledger add-source runs as the agent user)
apt-get install -y python3-pycryptodome >/dev/null 2>&1 || true

# Switch an existing ledger from WAL to a rollback journal (readers can't open WAL)
if [[ -e "$WS/ledger/ledger.db" ]]; then
  runuser -u farmdata -- sqlite3 "$WS/ledger/ledger.db" "PRAGMA journal_mode=DELETE;" >/dev/null
  rm -f "$WS/ledger/ledger.db-wal" "$WS/ledger/ledger.db-shm"
  chmod 644 "$WS/ledger/ledger.db"
fi

systemctl daemon-reload
systemctl enable --now ledger-ingest.timer
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  /opt/farm/bin/assemble-prompt "$inst"
done < /etc/farm/roles.conf
echo "Installed phase 2c. First run: sudo systemctl start ledger-ingest; journalctl -u ledger-ingest -f"
