#!/usr/bin/env bash
# Phase 10b: the money path on the five chains added in 10a (bsc, polygon, avalanche, optimism,
# hyperevm).
#  - /opt/farm/lib/farmchains.py: one table of chain ids, Chainlink native/USD Standard feeds,
#    USDC decimals (bsc 18), plausible price ranges and per-tx gas limits (hyperevm 2M); gate-ctl,
#    farm-signer and farm-watchdog import it instead of their own ethereum/base/arbitrum constants
#  - gate-ctl: USDC amounts in each chain's decimals; native price sanity per chain; tip from
#    eth_maxPriorityFeePerGas on the new chains (Polygon minimum); gas reserve for the funding
#    transfers on the new chains; hyperevm promote refused before funding when the executor
#    deployment would not fit 2M gas
#  - farm-signer: per-chain feed description (POL or MATIC / USD ...); a feed that fails at start on
#    a new chain disables that chain only (core chains still stop the signer); per-chain price range,
#    USDC decimals and gas limit; only the bot's own chain's USDC address counts as the USDC token
#  - farm-watchdog: per-chain USDC decimals; one chain's RPC failure no longer skips the others
#  - gate.json: chains + usdc for the five, gas_wallet_cap_usd optimism 18
#  - common.md: new chains promotable, OP Mainnet under the cap, HyperEVM 2M gas
# Every check (patch texts, chains against farmchains through the relay, offline tests including the
# 9i/9j/9k suites) runs before anything changes. If farm-signer or farm-watchdog does not come back
# after the restart, the programs and gate.json are restored and restarted. Backups: .<name>.bak-10b.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin L=/opt/farm/lib E=/etc/farm P=/srv/farm/prompts
HERE=$(pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
INST=("$B/gate-ctl" "$B/farm-signer" "$B/farm-watchdog" "$P/common.md")

python3 -I -m py_compile farmchains.py cfg-10b.py patch-10b.py test-10b.py regress/test-9i.py regress/test-9j.py regress/test-9k.py
echo "== patch texts"
python3 -I patch-10b.py check "${INST[@]}"
echo "== chains through the relay, against farmchains (nothing changed yet)"
python3 -I cfg-10b.py verify "$HERE"
echo "== gate.json (plan)"
python3 -I cfg-10b.py plan "$E/gate.json"
python3 -I patch-10b.py apply "${INST[@]}" "$tmp" >/dev/null
echo "== farmchains.py -> $L (inert until the programs below import it)"
install -o root -g root -m 644 farmchains.py "$L/farmchains.py"
python3 -I -m py_compile "$tmp/gate-ctl" "$tmp/farm-signer" "$tmp/farm-watchdog"
echo "== offline tests"
python3 -I test-10b.py "${INST[@]:0:3}" "$P/common.md" "$HERE" --old || true
python3 -I test-10b.py "$tmp/gate-ctl" "$tmp/farm-signer" "$tmp/farm-watchdog" "$tmp/common.md" "$HERE"
echo "== regression (9i / 9j / 9k suites on the 10b files)"
python3 -I regress/test-9i.py "$tmp/gate-ctl" "$tmp/farm-watchdog" | tail -1
python3 -I regress/test-9j.py "$tmp/gate-ctl" | tail -1
python3 -I regress/test-9k.py "$tmp/gate-ctl" "$B/run-role" | tail -1

echo "== backups"
bak() { local d f; d=$(dirname "$1"); f=$(basename "$1"); [[ -e "$d/.$f.bak-10b" ]] || cp -a "$1" "$d/.$f.bak-10b"; }
for f in "${INST[@]}" "$E/gate.json"; do bak "$f"; done

rollback() {
  echo "!! $1 - restoring the pre-10b programs and gate.json" >&2
  for f in gate-ctl farm-signer farm-watchdog; do cp -a "$B/.$f.bak-10b" "$B/$f"; done
  cp -a "$E/.gate.json.bak-10b" "$E/gate.json"
  systemctl restart farm-signer farm-watchdog || true
  sleep 5
  systemctl is-active farm-signer farm-watchdog || true
  journalctl -u farm-signer -u farm-watchdog -n 30 --no-pager || true
  exit 1
}

echo "== install"
put() { install -o "$(stat -c %u "$2")" -g "$(stat -c %g "$2")" -m "$(stat -c %a "$2")" "$1" "$2"; }
put "$tmp/gate-ctl" "$B/gate-ctl"
put "$tmp/farm-signer" "$B/farm-signer"
put "$tmp/farm-watchdog" "$B/farm-watchdog"
python3 -I cfg-10b.py apply "$E/gate.json"
since=$(date '+%Y-%m-%d %H:%M:%S')
systemctl restart farm-signer farm-watchdog
sleep 8
for u in farm-signer farm-watchdog; do
  systemctl is-active --quiet "$u" || rollback "$u is not active after the restart"
done
echo "farm-signer and farm-watchdog active"
journalctl -u farm-signer -u farm-watchdog --since "$since" --no-pager | tail -n 15
grep -h '"chain_disabled"' /var/lib/farmgate/signer.log 2>/dev/null | tail -n 5 || true

echo "== gate status"
sudo -u harness /opt/farm/bin/gate status > "$tmp/status.out" || rollback "gate status failed"
python3 -I - "$tmp/status.out" <<'EOF' || cat "$tmp/status.out"
import json, sys
s = json.load(open(sys.argv[1]))
print("capital_usd", s.get("capital_usd"), "/", s.get("max_capital_usd"), " frozen", s.get("frozen"), " halted", s.get("halted"))
print("gas_wallet_cap_usd", s.get("gas_wallet_cap_usd"))
for k, v in sorted((s.get("intermediate_balances_usd") or {}).items()):
    print(f"  intermediate {k}: {v}")
print("live bots:", ", ".join(sorted(s.get("live") or {})))
EOF

echo "== common.md and prompts"
put "$tmp/common.md" "$P/common.md"
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  /opt/farm/bin/assemble-prompt "$inst"
done < "$E/roles.conf"
note=/srv/farm/ws/inbox/meta/2026-11-10-phase10b-money-path.md
[[ -e $note ]] || install -m 664 inbox-meta-2026-11-10-phase10b-money-path.md "$note"
echo "Installed phase 10b. Paste everything from '== patch texts' down."
