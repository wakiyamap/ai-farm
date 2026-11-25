#!/usr/bin/env bash
# Phase 10a: five new chains on the read side - bsc (56), polygon (137), avalanche (43114),
# optimism (10), hyperevm (999).
#  - relay.json / chains (kb) / ledger.json gain the chains; fork-<chain>.env + fork@<chain> on 9004-9008
#  - fork CLI knows the ports; farm.nft lets the earner and bots reach 9001-9008 (9013 stays closed)
#  - ledger-ingest: one unreadable chain head no longer fails the whole run
#  - common.md lists the eight chains and says the gate cannot promote on the new ones yet
#  - a note for meta (TOOLS.md / role files)
# The gate, signer and watchdog are NOT touched: gate.json has no entry for the new chains, so
# `gate promote` keeps refusing them until 10b.
# Order: every check (patch texts, endpoint chain ids, offline tests, nft syntax) runs before anything
# changes. Backups: .<name>.bak-10a next to each changed file. Safe to re-run.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin E=/etc/farm P=/srv/farm/prompts
NEW="bsc polygon avalanche optimism hyperevm"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
INST=("$B/fork" "$E/farm.nft" "$P/common.md" "$B/ledger-ingest")

python3 -I -m py_compile cfg-10a.py patch-10a.py test-10a.py
echo "== patch texts"
python3 -I patch-10a.py check "${INST[@]}"
echo "== endpoints (direct, before any change)"
python3 -I cfg-10a.py preflight
python3 -I patch-10a.py apply "${INST[@]}" "$tmp" >/dev/null
python3 -I -m py_compile "$tmp/fork" "$tmp/ledger-ingest"
nft -c -f "$tmp/farm.nft"
echo "== offline tests"
python3 -I test-10a.py "${INST[@]}" cfg-10a.py --old || true
python3 -I test-10a.py "$tmp/fork" "$tmp/farm.nft" "$tmp/common.md" "$tmp/ledger-ingest" cfg-10a.py

echo "== backups"
bak() { local d f; d=$(dirname "$1"); f=$(basename "$1"); [[ -e "$d/.$f.bak-10a" ]] || cp -a "$1" "$d/.$f.bak-10a"; }
for f in "${INST[@]}" "$E/chains" "$E/relay.json" "$E/ledger.json"; do bak "$f"; done

echo "== config"
python3 -I cfg-10a.py apply "$E"
echo "== relay restart (fork@ units restart with it: fork state resets, generations stay)"
systemctl restart rpc-relay
python3 -I - <<'EOF'
import json, time, urllib.request
for _ in range(30):
    try:
        h = json.load(urllib.request.urlopen("http://127.0.0.1:8545/health", timeout=3))
        if all(c in h["chains"] for c in ("bsc", "polygon", "avalanche", "optimism", "hyperevm")):
            print("relay health:", ", ".join(h["chains"]))
            break
    except OSError:
        pass
    time.sleep(1)
else:
    raise SystemExit("relay did not come back with the new chains")
EOF
python3 -I cfg-10a.py verify
put() { install -o "$(stat -c %u "$2")" -g "$(stat -c %g "$2")" -m "$(stat -c %a "$2")" "$1" "$2"; }
put "$tmp/ledger-ingest" "$B/ledger-ingest"      # before ledger.json names the new chains
python3 -I cfg-10a.py ledger "$E"

echo "== files"
put "$tmp/fork" "$B/fork"
put "$tmp/common.md" "$P/common.md"
put "$tmp/farm.nft" "$E/farm.nft"
systemctl restart farm-nft
nft list table inet farm | grep -c '9001-9008' | sed 's/^/nft rules with 9001-9008: /' || true

echo "== forks"
for c in $NEW; do systemctl enable --now "fork@$c" 2>&1 | grep -v '^Created symlink' || true; done
for _ in $(seq 1 45); do
  # ethereum-review is always "down" for the earner (nft); count only the new forks
  down=$(sudo -u earner /opt/farm/bin/fork status 2>/dev/null | grep -cE $'^(bsc|polygon|avalanche|optimism|hyperevm)\tdown' || true)
  [[ "$down" == 0 ]] && break
  sleep 2
done
sudo -u earner /opt/farm/bin/fork status
for c in $NEW; do sudo -u earner /opt/farm/bin/fork info "$c" || true; done
echo "bots (farmbot) reach the new forks:"
sudo -u farmbot /opt/farm/bin/fork status hyperevm || true

echo "== prompts and meta note"
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  /opt/farm/bin/assemble-prompt "$inst"
done < "$E/roles.conf"
grep -c 'BNB Smart Chain (56)' /srv/farm/runners/*/prompt.md | sed 's/^/  /' || true
note=/srv/farm/ws/inbox/meta/2026-11-10-phase10a-new-chains.md
[[ -e $note ]] || install -m 664 inbox-meta-2026-11-10-phase10a-new-chains.md "$note"
echo "Installed phase 10a. Paste everything from '== patch texts' down. Gate/signer/watchdog unchanged (10b)."
