#!/usr/bin/env bash
# Phase 15h (2026-11-19): the fork lane never reads old state from a public node.
#  meta (inbox/meta/2026-11-19-bsc-fork-missing-trie-node.md): a bsc fork at a 4-day-old block got
#  `missing trie node` now and then and once went down with `no provider available`. The relay keeps
#  one cooldown per upstream URL for all lanes; while Alchemy was cooling down after another lane's
#  timeout or rate limit, the fork's read of old state went to bsc-dataseed (recent state only).
#  - rpc-relay (6 text patches):
#    1. fork lane + state read older than public nodes keep: Alchemy only
#    2. a fork's only archive provider and every send (Alchemy only) are tried even while cooling down
#    3. fork lane: a rate limit goes back as JSON-RPC code 429 ("rate limited, retry"), which anvil
#       retries with backoff, instead of -32000
#  Other lanes and methods are unchanged. relay.json, units and other programs are not touched.
#  A note for meta goes to inbox/meta.
#  rpc-relay is restarted (live bots and forks lose reads for a few seconds). If it does not come back
#  or a service is not active afterwards, the old rpc-relay is restored.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
export PYTHONDONTWRITEBYTECODE=1
sha() { sha256sum "$1" | cut -d' ' -f1; }
RELAY_15E=89f94742647ba2e998e9a7286e8a80f30c9c32a0eedf08d75eb73f1a55d9bbfd
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
health() { curl -s -m 5 http://127.0.0.1:8545/health; }

echo "== checks (nothing is changed yet)"
for f in patch-15h.py test-15h.py regress-15e.py regress-15c.py; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$f"
done
hr=$(sha $B/rpc-relay)
echo "  rpc-relay sha256 (reference after 15e / installed)"
echo "    $RELAY_15E"
echo "    $hr"
if grep -q '# 15h: a fork' $B/rpc-relay; then
  echo "  already the 15h version"; cp $B/rpc-relay "$tmp/"; NEWFILE=0
else
  [[ $hr == "$RELAY_15E" ]] || echo "  note: rpc-relay differs from the 15e version; the text patches decide"
  python3 -I -B patch-15h.py check $B/rpc-relay
  python3 -I -B patch-15h.py apply $B/rpc-relay "$tmp"
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$tmp/rpc-relay"
  NEWFILE=1
fi
echo "== offline tests (installed rpc-relay: report only, 5 of 10 before 15h)"
python3 -I -B test-15h.py $B/rpc-relay --old | tail -1
echo "== offline tests (patched rpc-relay)"
python3 -I -B test-15h.py "$tmp/rpc-relay"
echo "== regression: the 15e and 15c tests on the patched rpc-relay"
python3 -I -B regress-15e.py "$tmp/rpc-relay" $B/farm-watchdog | tail -1
python3 -I -B regress-15c.py "$tmp/rpc-relay" $B/farm-hermes | tail -1

back() {
  echo "!! $1 - restoring rpc-relay" >&2
  [[ -f $B/.rpc-relay.bak-15h ]] && cp -a $B/.rpc-relay.bak-15h $B/rpc-relay
  systemctl restart rpc-relay.service || true
  sleep 5
  systemctl is-active rpc-relay.service farm-signer.service farm-watchdog.service farm-feed.service || true
  journalctl -u rpc-relay -n 15 --no-pager >&2 || true
  exit 1
}

if (( NEWFILE )); then
  echo "== install"
  [[ -e $B/.rpc-relay.bak-15h ]] || cp -a $B/rpc-relay $B/.rpc-relay.bak-15h
  install -o "$(stat -c %u $B/rpc-relay)" -g "$(stat -c %g $B/rpc-relay)" -m "$(stat -c %a $B/rpc-relay)" \
    "$tmp/rpc-relay" $B/rpc-relay
  systemctl restart rpc-relay.service
  ok=0
  for _ in $(seq 1 20); do
    if health | python3 -I -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("ok") and "cycle" in d else 1)' 2>/dev/null; then ok=1; break; fi
    sleep 1
  done
  (( ok )) || back "rpc-relay does not answer /health"
  sleep 8
  systemctl is-active rpc-relay.service farm-signer.service farm-watchdog.service farm-feed.service \
    || back "a service is not active after the relay restart"
fi

echo "== probe: farmfork reads old bsc state through the relay (one eth_getBalance, about 20 CU)"
runuser -u farmfork -- python3 -I -B - <<'PY' || echo "  (probe could not run; 15h is still installed)"
import json, urllib.request
def post(body, path="/bsc?lane=research"):
    r = urllib.request.Request("http://127.0.0.1:8545" + path, data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=40).read())
lane = json.loads(urllib.request.urlopen("http://127.0.0.1:8545/lane?lane=research", timeout=5).read())["lane"]
print("  lane for farmfork:", lane, "(expected fork)")
head = int(post({"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []})["result"], 16)
old = head - 200_000                      # about a day of bsc blocks: far older than public nodes keep
WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
out = post({"jsonrpc": "2.0", "id": 2, "method": "eth_getBalance", "params": [WBNB, hex(old)]})
if "result" in out:
    print(f"  block {old} (head {head}): WBNB contract balance {int(out['result'], 16) / 1e18:,.0f} BNB - ok")
else:
    print(f"  block {old}: ERROR {out.get('error')}")
    print("  missing trie node here would mean 15h did not take effect; code 429 means Alchemy was rate-limited, try again")
PY
for f in $(systemctl list-units --plain --no-legend --state=active 'fork@*.service' | awk '{print $1}'); do echo "  $f active"; done

echo "== note for meta"
install -o root -g root -m 644 inbox-meta-2026-11-19-phase15h-fork-archive.md /srv/farm/ws/inbox/meta/2026-11-19-phase15h-fork-archive.md
echo "  inbox/meta/2026-11-19-phase15h-fork-archive.md"

echo "== sha256 (expected = patched copy checked above / installed)"
echo "  rpc-relay  $(sha "$tmp/rpc-relay")"
echo "             $(sha $B/rpc-relay)"
echo "Installed phase 15h. A fork's old-state read never goes to a public node; fork/public in the brief should show no new failures."
echo "To undo: cp -a $B/.rpc-relay.bak-15h $B/rpc-relay && systemctl restart rpc-relay"
