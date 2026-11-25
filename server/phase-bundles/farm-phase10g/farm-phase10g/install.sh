#!/usr/bin/env bash
# Phase 10g: a ninth chain, elysium (Kinetiq's Arbitrum Orbit chain that settles to HyperEVM; chain
# id 99901, gas token HYPE, mainnet since 2026-11-09). Read side and money path in one bundle.
#  read side   relay.json / chains (kb) / ledger.json gain elysium; fork-elysium.env + fork@elysium on
#              9009; fork CLI knows the port; farm.nft lets the earner and bots reach 9001-9009
#  money path  /opt/farm/lib/farmchains.py gains elysium, priced with the HYPE / USD feed on hyperevm
#              (feed_chain; human decision 2026-11-11), and marks arbitrum and elysium as Nitro chains;
#              gate-ctl / farm-signer / farm-watchdog read a feed on its own chain; the gate estimates
#              gas for its own transfers on Nitro chains (a plain transfer needs more than 21,000 gas
#              there - this also fixes funding and sweeping on arbitrum, which no bot had used yet);
#              gate.json: chains += elysium, usdc.elysium
#  prompts     common.md names the chain and what is different there; a note for meta
# Order: every check that needs no change runs first (patch texts, the public and Alchemy endpoints
# directly, offline tests incl. the 10e and 10f suites). Then the read side; then `verify` through the
# relay (chain id, USDC 6 decimals + symbol, the feed) - a mismatch stops before the money path is
# touched. If farm-signer or farm-watchdog does not come back, or gate status fails, the programs,
# farmchains.py and gate.json are restored. Backups: .<name>.bak-10g. Safe to re-run.
# The Alchemy subdomain defaults to elysium-mainnet; override with FARM_ELYSIUM_ALCHEMY=<subdomain>:
#   sudo FARM_ELYSIUM_ALCHEMY=<subdomain> ./farm-phase10g/install.sh
# The relay restart also restarts the fork@ units (fork state resets) and interrupts reads for a moment.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin L=/opt/farm/lib E=/etc/farm P=/srv/farm/prompts
HERE=$(pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
export PYTHONDONTWRITEBYTECODE=1
INST=("$B/gate-ctl" "$B/farm-signer" "$B/farm-watchdog" "$B/fork" "$E/farm.nft" "$P/common.md")
pyc() { python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$1"; }

for f in farmchains.py cfg-10g.py patch-10g.py test-10g.py regress/test-10e.py regress/test-10f.py; do pyc "$f"; done
echo "== patch texts"
python3 -I -B patch-10g.py check "${INST[@]}"
echo "== endpoints (direct, before any change)"
python3 -I -B cfg-10g.py preflight
python3 -I -B patch-10g.py apply "${INST[@]}" "$tmp" >/dev/null
for f in gate-ctl farm-signer farm-watchdog fork; do pyc "$tmp/$f"; done
nft -c -f "$tmp/farm.nft"
echo "== offline tests"
python3 -I -B test-10g.py "$B/gate-ctl" "$B/farm-signer" "$B/farm-watchdog" "$HERE" --old || true
python3 -I -B test-10g.py "$tmp/gate-ctl" "$tmp/farm-signer" "$tmp/farm-watchdog" "$HERE"
echo "== regression (10e and 10f suites on the 10g files)"
python3 -I -B regress/test-10e.py "$tmp/gate-ctl" "$tmp/farm-signer" "$tmp/farm-watchdog" "$HERE" | tail -1
python3 -I -B regress/test-10f.py "$tmp/gate-ctl" "$HERE" | tail -1
echo "== gate.json (plan)"
python3 -I -B cfg-10g.py gate-plan "$E/gate.json"

echo "== backups"
bak() { local d f; d=$(dirname "$1"); f=$(basename "$1"); [[ -e "$d/.$f.bak-10g" ]] || cp -a "$1" "$d/.$f.bak-10g"; }
for f in "${INST[@]}" "$L/farmchains.py" "$E/chains" "$E/relay.json" "$E/ledger.json" "$E/gate.json"; do bak "$f"; done

echo "== read side: config"
python3 -I -B cfg-10g.py apply "$E"
echo "== relay restart (fork@ units restart with it: fork state resets, generations stay)"
systemctl restart rpc-relay
python3 -I -B - <<'EOF'
import json, time, urllib.request
for _ in range(30):
    try:
        h = json.load(urllib.request.urlopen("http://127.0.0.1:8545/health", timeout=3))
        if "elysium" in h["chains"]:
            print("relay health:", ", ".join(h["chains"]))
            break
    except OSError:
        pass
    time.sleep(1)
else:
    raise SystemExit("relay did not come back with elysium")
EOF
echo "== verify through the relay (a mismatch stops here; the money path is untouched until this passes)"
python3 -I -B cfg-10g.py verify
python3 -I -B cfg-10g.py ledger "$E"

rollback() {
  echo "!! $1 - restoring the pre-10g programs, farmchains.py and gate.json" >&2
  for f in gate-ctl farm-signer farm-watchdog; do cp -a "$B/.$f.bak-10g" "$B/$f"; done
  cp -a "$L/.farmchains.py.bak-10g" "$L/farmchains.py"
  cp -a "$E/.gate.json.bak-10g" "$E/gate.json"
  systemctl restart farm-signer farm-watchdog || true
  sleep 5
  systemctl is-active farm-signer farm-watchdog || true
  journalctl -u farm-signer -u farm-watchdog -n 30 --no-pager || true
  exit 1
}

echo "== money path"
put() { install -o "$(stat -c %u "$2")" -g "$(stat -c %g "$2")" -m "$(stat -c %a "$2")" "$1" "$2"; }
put farmchains.py "$L/farmchains.py"            # first: the old programs run unchanged with the new table
put "$tmp/gate-ctl" "$B/gate-ctl"
put "$tmp/farm-signer" "$B/farm-signer"
put "$tmp/farm-watchdog" "$B/farm-watchdog"
python3 -I -B cfg-10g.py gate-apply "$E/gate.json"
since=$(date '+%Y-%m-%d %H:%M:%S')
systemctl restart farm-signer farm-watchdog
sleep 25                                   # the signer's feed check (9 chains) and one watchdog round
for u in farm-signer farm-watchdog; do
  systemctl is-active --quiet "$u" || rollback "$u is not active after the restart"
done
echo "farm-signer and farm-watchdog active"
journalctl -u farm-signer -u farm-watchdog --since "$since" --no-pager | tail -n 12
if journalctl -u farm-signer --since "$since" --no-pager | grep -q 'disabled'; then
  echo "!! the signer disabled a chain at start (see above): it will not sign there until restarted with the feed readable"
fi
sudo -u harness /opt/farm/bin/gate status > "$tmp/status.out" || rollback "gate status failed"
python3 -I -B - "$tmp/status.out" <<'EOF' || cat "$tmp/status.out"
import json, sys
s = json.load(open(sys.argv[1]))
print("capital_usd", s.get("capital_usd"), "/", s.get("max_capital_usd"), " daily_loss_usd", s.get("daily_loss_usd"),
      " frozen", s.get("frozen"), " halted", s.get("halted"))
ib = s.get("intermediate_balances_usd") or {}
print("  intermediate elysium:", ib.get("elysium"), "USD of HYPE,", ib.get("elysium:usdc"), "USDC")
for b, v in sorted((s.get("live") or {}).items()):
    print(f"  {b}: {v.get('service')}  {v.get('balances_usd')}")
EOF

echo "== fork CLI, nft, common.md"
put "$tmp/fork" "$B/fork"
put "$tmp/common.md" "$P/common.md"
put "$tmp/farm.nft" "$E/farm.nft"
systemctl restart farm-nft
nft list table inet farm | grep -c '9001-9009' | sed 's/^/nft rules with 9001-9009: /' || true
echo "== fork@elysium"
systemctl enable --now fork@elysium 2>&1 | grep -v '^Created symlink' || true
for _ in $(seq 1 45); do
  down=$(sudo -u earner /opt/farm/bin/fork status 2>/dev/null | grep -cE $'^elysium\tdown' || true)
  [[ "$down" == 0 ]] && break
  sleep 2
done
sudo -u earner /opt/farm/bin/fork status || true
sudo -u earner /opt/farm/bin/fork info elysium || echo "!! fork@elysium is not answering: journalctl -u fork@elysium -n 30 (the rest of 10g is installed and does not depend on it)"

echo "== prompts and meta note"
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  /opt/farm/bin/assemble-prompt "$inst"
done < "$E/roles.conf"
grep -c 'Elysium (99901)' /srv/farm/runners/*/prompt.md | sed 's/^/  /' || true
note=/srv/farm/ws/inbox/meta/2026-11-11-phase10g-elysium.md
[[ -e $note ]] || install -m 664 inbox-meta-2026-11-11-phase10g-elysium.md "$note"
echo "Installed phase 10g. Paste everything from '== patch texts' down."
