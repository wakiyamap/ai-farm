#!/usr/bin/env bash
# Phase 6x (inbox/human/2026-11-07-meta-websearch-assettransfers-kbkeys.md):
#  - rpc-relay: an upstream HTTP error now carries the provider's reason text (API key scrubbed),
#    so "alchemy: HTTP 400" on alchemy_getAssetTransfers shows what Alchemy objects to.
#  - KB: hyphenated protocols.protocol keys renamed to the underscore convention (backup first,
#    skipped when the underscore name already exists on that chain).
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/rpc-relay
install -o root -g root -m 755 opt/farm/bin/rpc-relay /opt/farm/bin/
systemctl restart rpc-relay.service
sleep 2

DB=/srv/farm/ws/kb/knowledge.db
OWNER=$(stat -c %U "$DB")
cp -a "$DB" "$DB.bak-6x-$(date +%Y%m%d%H%M)"
sudo -u "$OWNER" python3 -I - "$DB" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1], timeout=30)
rows = con.execute("SELECT id, chain, protocol FROM protocols WHERE protocol LIKE '%-%'").fetchall()
for rid, chain, name in rows:
    new = name.replace("-", "_")
    if con.execute("SELECT id FROM protocols WHERE chain=? AND protocol=?", (chain, new)).fetchone():
        print(f"skip protocols:{rid} {chain} {name}: {new} already exists"); continue
    con.execute("UPDATE protocols SET protocol=? WHERE id=?", (new, rid))
    print(f"protocols:{rid} {chain} {name} -> {new}")
con.commit()
PY
echo "== relay error detail check (expect Alchemy's reason after HTTP 400, or a result)"
curl -s -m 20 -H 'content-type: application/json' --data \
 '{"jsonrpc":"2.0","id":1,"method":"alchemy_getAssetTransfers","params":[{"fromBlock":"0x0","toBlock":"latest","category":["external"],"maxCount":"0x1","toAddress":"0x0000000000000000000000000000000000000000"}]}' \
 'http://127.0.0.1:8545/ethereum?lane=research' | head -c 600; echo
echo "Installed phase 6x."
