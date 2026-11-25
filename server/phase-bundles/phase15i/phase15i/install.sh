#!/usr/bin/env bash
# Phase 15i (2026-11-20): fork lane on Alchemy only with no cap, bigger read budgets, feed filters,
# builder session context. Human decisions of 2026-11-20 (farm/ops/2026-11-20-0113.md, -0129.md).
#  - rpc-relay (text patch): every fork-lane read goes to Alchemy only, whatever the block and the
#    day's spend. 15h relied on is_historical(), which missed anvil's reads, so forks still hit public
#    nodes (`public: HTTP 403 Archive`).
#  - relay.json: fork 600k -> 95.2M (shown only; the relay no longer caps the fork lane),
#    research 700k -> 1.5M, scout 300k -> 1.2M CU/day.
#  - feed.json: max_log_filters_per_chain 8 -> 16.
#  - /opt/farm/context/earner: fix list reads the current decision (first decision line or heading),
#    resubmitted bots listed apart, measured leads with a bot or marked done left out.
#  - /opt/farm/context/builder: "Trial bots live: N / 45".
#  rpc-relay and farm-feed are restarted (reads pause for a few seconds; feed callers poll meanwhile).
#  On failure everything is restored from the .bak-15i copies.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
export PYTHONDONTWRITEBYTECODE=1
B=/opt/farm/bin; C=/opt/farm/context; E=/etc/farm
sha() { sha256sum "$1" | cut -d' ' -f1; }
health() { curl -s -m 5 http://127.0.0.1:8545/health; }
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# reference sha256 of the files sent on 2026-11-20 01:42 JST (farm-15i-src.tgz)
declare -A REF=(
  [$B/rpc-relay]=1c5e781b34c9ae725421222d9b1ec070e2332dd33608c5a39917af818271369e
  [$C/earner]=0412faf8660d0a56c339ef8ccb06ee2a0c7e4cee6e6a2d9be7d574d36f8f597e
  [$C/builder]=7aa638a2752c6fa879071c5553104e9a7d29f89d6e182d550cfd9661b4bd76b5
  [$E/relay.json]=ba248582d9d64c03c5a9cb04b0d70be598aeec52756bde26365e09016fc9c9b3
  [$E/feed.json]=915c5cb752381d355e4c2a9875567d3118d0e5f4fb4bff85fa65143babf7248c
)
FILES=("$B/rpc-relay" "$C/earner" "$C/builder" "$E/relay.json" "$E/feed.json")

echo "== checks (nothing is changed yet)"
for f in patch-15i.py cfg-15i.py test-15i.py; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$f"
done
echo "  sha256 (reference = sent 11-20 01:42 / installed)"
for f in "${FILES[@]}"; do
  echo "  $f"; echo "    ${REF[$f]}"; echo "    $(sha "$f")"
  [[ $(sha "$f") == "${REF[$f]}" ]] || echo "    note: differs from the reference; the patches decide"
done
python3 -I -B patch-15i.py apply $B/rpc-relay $C/earner $C/builder "$tmp"
python3 -I -B cfg-15i.py apply $E/relay.json $E/feed.json "$tmp"
python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$tmp/rpc-relay"
bash -n "$tmp/earner"; bash -n "$tmp/builder"

echo "== offline tests (installed files: report only, 7 of 16 before 15i)"
python3 -I -B test-15i.py $B/rpc-relay $C/earner $C/builder --old | tail -1
echo "== offline tests (new files)"
python3 -I -B test-15i.py "$tmp/rpc-relay" "$tmp/earner" "$tmp/builder"

back() {
  echo "!! $1 - restoring the 15i files" >&2
  for f in "${FILES[@]}"; do
    d=$(dirname "$f"); b=$(basename "$f")
    [[ -f "$d/.$b.bak-15i" ]] && cp -a "$d/.$b.bak-15i" "$f"
  done
  systemctl restart rpc-relay.service || true
  sleep 15
  systemctl restart farm-feed.service || true
  sleep 5
  systemctl is-active rpc-relay.service farm-signer.service farm-watchdog.service farm-feed.service || true
  journalctl -u rpc-relay -n 15 --no-pager >&2 || true
  exit 1
}

echo "== install"
for f in "${FILES[@]}"; do
  d=$(dirname "$f"); b=$(basename "$f")
  [[ -e "$d/.$b.bak-15i" ]] || cp -a "$f" "$d/.$b.bak-15i"
  install -o "$(stat -c %u "$f")" -g "$(stat -c %g "$f")" -m "$(stat -c %a "$f")" "$tmp/$b" "$f"
  echo "  $f"
done
systemctl restart rpc-relay.service
ok=0
for _ in $(seq 1 20); do
  if health | python3 -I -c 'import json,sys; d=json.load(sys.stdin); b=d.get("budget",{}); sys.exit(0 if d.get("ok") and b.get("research")==1500000 and b.get("scout")==1200000 else 1)' 2>/dev/null; then ok=1; break; fi
  sleep 1
done
(( ok )) || back "rpc-relay does not answer /health with the new budgets"
echo "  rpc-relay /health ok (research 1,500,000 / scout 1,200,000)"
sleep 15                                   # fork@ units restart with the relay; let them settle (15h note)
systemctl restart farm-feed.service
sleep 8
systemctl is-active rpc-relay.service farm-signer.service farm-watchdog.service farm-feed.service \
  || back "a service is not active after the restarts"
journalctl -u farm-feed -n 3 --no-pager | sed 's/^/  feed: /' || true

echo "== probe: farmfork reads old arbitrum state through the relay (about 40 CU)"
runuser -u farmfork -- python3 -I -B - <<'PY' || echo "  (probe could not run; 15i is still installed)"
import json, urllib.request
def post(body, path="/arbitrum?lane=research"):
    r = urllib.request.Request("http://127.0.0.1:8545" + path, data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=60).read())
lane = json.loads(urllib.request.urlopen("http://127.0.0.1:8545/lane?lane=research", timeout=5).read())["lane"]
print("  lane for farmfork:", lane, "(expected fork)")
head = int(post({"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []})["result"], 16)
WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
for back_blocks in (400, 400_000):         # ~100 s (15h treated as recent) and ~1 day old
    blk = head - back_blocks
    out = post({"jsonrpc": "2.0", "id": 2, "method": "eth_getBalance", "params": [WETH, hex(blk)]})
    if "result" in out:
        print(f"  block {blk} (head - {back_blocks}): WETH contract {int(out['result'], 16) / 1e18:,.0f} ETH - ok")
    else:
        print(f"  block {blk} (head - {back_blocks}): ERROR {out.get('error')}")
PY
for f in $(systemctl list-units --plain --no-legend --state=active 'fork@*.service' | awk '{print $1}'); do echo "  $f active"; done

echo "== builder context (first lines of the changed sections)"
$C/builder builder-claude 2>/dev/null | grep -A4 -E '^### (Paper bots waiting|Paper bots resubmitted|Measured leads|Trial bots live)' | sed 's/^/  /' | head -40 || true

echo "== note for meta"
install -o root -g root -m 644 inbox-meta-2026-11-20-phase15i-fork-alchemy-budgets.md \
  /srv/farm/ws/inbox/meta/2026-11-20-phase15i-fork-alchemy-budgets.md
echo "  inbox/meta/2026-11-20-phase15i-fork-alchemy-budgets.md"

echo "== sha256 (expected = new file built above / installed)"
for f in "${FILES[@]}"; do
  echo "  $f"; echo "    $(sha "$tmp/$(basename "$f")")"; echo "    $(sha "$f")"
done
echo "Installed phase 15i. fork/public in the brief should stay at its current count from now on."
echo "To undo: for each file, cp -a <dir>/.<name>.bak-15i <file>; then restart rpc-relay, wait 15 s, restart farm-feed"
