#!/usr/bin/env bash
# Phase 15f (2026-11-19): relay.json gets https://bsc-dataseed.binance.org as the first public bsc
# node (the old bsc-dataseed.bnbchain.org does not serve eth_getLogs, so bsc reads failed whenever a
# lane's Alchemy budget was spent). rpc-relay is restarted; if it does not come back or bsc does not
# answer through it, relay.json is restored. A note for meta. Nothing else changes.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
RJ=/etc/farm/relay.json
REF=7b4313a3cd543dd06c119f1023062b4cd5809ea457ec66ef15c5acb4788d2382   # after 15e
URL=https://bsc-dataseed.binance.org
sha() { sha256sum "$1" | cut -d' ' -f1; }
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
rpc() {  # rpc <url> <method> <params-json>
  curl -s -m 15 -H 'Content-Type: application/json' -A farm-rpc-relay/1.0 \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"$2\",\"params\":$3}" "$1"
}

echo "== checks (nothing is changed yet)"
echo "  relay.json sha256 (reference after 15e / now)"
echo "    $REF"
echo "    $(sha $RJ)"
python3 -I -B cfg-15f.py show $RJ
python3 -I -B cfg-15f.py apply $RJ "$tmp/relay.json" > /dev/null
python3 -I -B -c 'import json,sys; json.load(open(sys.argv[1]))' "$tmp/relay.json"
cid=$(rpc $URL eth_chainId '[]' | python3 -I -c 'import json,sys; print(json.load(sys.stdin).get("result"))')
echo "  $URL eth_chainId: $cid (expected 0x38)"
[[ $cid == 0x38 ]] || { echo "  the node is not BNB Smart Chain or does not answer. Nothing was changed." >&2; exit 1; }
head=$(rpc $URL eth_blockNumber '[]' | python3 -I -c 'import json,sys; print(int(json.load(sys.stdin)["result"],16))')
from=$(printf '0x%x' $((head - 2000))); to=$(printf '0x%x' $head)
USDT=0x55d398326f99059fF775485246999027B3197955
n=$(rpc $URL eth_getLogs "[{\"fromBlock\":\"$from\",\"toBlock\":\"$to\",\"address\":\"$USDT\"}]" \
    | python3 -I -c 'import json,sys; d=json.load(sys.stdin); print(len(d["result"]) if "result" in d else "ERR " + str(d.get("error"))[:120])')
echo "  eth_getLogs (USDT, last 2,000 blocks) direct: $n logs"

back() {
  echo "!! $1 - restoring relay.json" >&2
  [[ -f $RJ.bak-15f ]] && cat "$RJ.bak-15f" > $RJ
  systemctl restart rpc-relay.service || true
  sleep 5
  systemctl is-active rpc-relay.service farm-signer.service farm-watchdog.service || true
  exit 1
}
echo "== install"
[[ -e $RJ.bak-15f ]] || cp -a $RJ $RJ.bak-15f
cat "$tmp/relay.json" > $RJ
systemctl restart rpc-relay.service
ok=0
for _ in $(seq 1 20); do
  curl -s -m 3 http://127.0.0.1:8545/health | grep -q '"ok": *true' && { ok=1; break; }
  sleep 1
done
(( ok )) || back "rpc-relay does not answer /health"
b=$(runuser -u harness -- python3 -I -c '
import json, urllib.request
r = urllib.request.Request("http://127.0.0.1:8545/bsc?lane=research", data=json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}).encode(), headers={"Content-Type":"application/json"})
print(int(json.loads(urllib.request.urlopen(r, timeout=15).read())["result"], 16))' 2>/dev/null || echo ERR)
echo "  bsc eth_blockNumber through the relay (research lane): $b"
[[ $b != ERR ]] || back "bsc does not answer through the relay"
sleep 5
systemctl is-active rpc-relay.service farm-signer.service farm-watchdog.service farm-feed.service || back "a service is not active after the relay restart"
python3 -I -B cfg-15f.py show $RJ
install -o root -g root -m 644 inbox-meta-2026-11-19-phase15f-bsc-public.md /srv/farm/ws/inbox/meta/2026-11-19-phase15f-bsc-public.md
echo "== sha256 (expected / installed)"
echo "  relay.json $(sha "$tmp/relay.json")"
echo "             $(sha $RJ)"
echo "Installed phase 15f. To undo: sudo sh -c 'cat $RJ.bak-15f > $RJ' && sudo systemctl restart rpc-relay"
