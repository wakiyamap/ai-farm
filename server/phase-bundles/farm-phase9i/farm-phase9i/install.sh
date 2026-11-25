#!/usr/bin/env bash
# Phase 9i (2026-11-10):
#  - gate promote: the funding pre-check asked the intermediate wallet for the uncapped native share
#    (moonwell-whale-base: capital_usd 120 -> "less than 120.00 USD + gas") although the Base gas
#    wallet cap means at most 18 USD is ever sent. It now checks the amount that will be sent.
#  - gate sweep: the USDC branch called the wait_receipt that 9f shadowed -> TypeError right after
#    the USDC transfer was broadcast (no PnL, no archive, a bot-key nonce the watchdog cannot
#    attribute; a second stop would book the whole principal as "principal gone"). Now: poll_receipt
#    with status checks, sweep_usdc_sent (with nonce) logged before waiting, and a transfer whose
#    receipt does not come back is kept "in flight" and settled from its receipt by the next sweep.
#    Native sweep records carry the nonce read before signing.
#  - gate stop --all: an exception on one bot no longer leaves the others running.
#  - farm-watchdog: chains are read with every YAML list style like gate/signer since 9e (it read
#    only a one-line `chains: [..]`; a block-list manifest left that bot unmonitored); sweep_usdc_sent
#    is a known gate nonce.
# The installed files are patched in place by exact text (each hunk must match exactly once), so
# nothing changes if they differ from phase 9g. Offline tests run before anything is installed.
# Safe to re-run.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "== patch check against the installed files"
python3 -I patch-9i.py check "$B/gate-ctl" "$B/farm-watchdog"
python3 -I patch-9i.py apply "$B/gate-ctl" "$B/farm-watchdog" "$tmp" >/dev/null
python3 -I -m py_compile "$tmp/gate-ctl" "$tmp/farm-watchdog"

echo "== offline tests (fake chain in a temp dir; no RPC, no keys, no gate state touched)"
python3 -I test-9i.py "$B/gate-ctl" "$B/farm-watchdog" --old || true
python3 -I test-9i.py "$tmp/gate-ctl" "$tmp/farm-watchdog"

for f in gate-ctl farm-watchdog; do
  [[ -e "$B/.$f.bak-9i" ]] || cp -a "$B/$f" "$B/.$f.bak-9i"
done
install -o root -g root -m 755 "$tmp/gate-ctl" "$tmp/farm-watchdog" "$B/"
systemctl restart farm-watchdog.service
sleep 3
systemctl is-active farm-watchdog.service

echo "== chains the watchdog reads for each live bot (before 9i -> now)"
python3 -I - <<'PY'
import glob, importlib.machinery, importlib.util, sys
sys.path[:0] = ["/opt/farm/pylib", "/opt/farm/lib"]
l = importlib.machinery.SourceFileLoader("wd", "/opt/farm/bin/farm-watchdog")
m = importlib.util.module_from_spec(importlib.util.spec_from_loader(l.name, l)); l.exec_module(m)
def old(text):
    chains = []
    for line in text.splitlines(True):
        if line.startswith("chains:"):
            chains = [c.strip().strip('"') for c in line.split(":", 1)[1].strip().strip("[]").split(",") if c.strip() in m.CHAIN_IDS]
    return chains
for p in sorted(glob.glob("/srv/farm/ws/bots/live/*/manifest.yaml")):
    t = open(p).read()
    o, n = old(t), m.manifest_chains(t)
    gap = sorted(set(n) - set(o))
    print(f"  {p.split('/')[-2]:32} {o} -> {n}" + (f"   <- was NOT monitored on {', '.join(gap)}" if gap else ""))
PY
journalctl -u farm-watchdog.service --since "-1min" --no-pager -n 5 | tail -n +2 || true
sudo -u harness /opt/farm/bin/gate status >/dev/null && echo "gate status: ok"
echo "Installed phase 9i."
