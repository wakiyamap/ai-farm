#!/usr/bin/env bash
# Phase 6w: rpc-relay no longer caches results keyed on moving block tags ("latest", "pending",
# "safe", "finalized", or an omitted block) for more than 1 s. eth_getBlockByNumber("latest")
# had a 600 s TTL, so heads and baseFees came back up to minutes old
# (inbox/human/2026-11-07-meta-relay-latest-stale.md).
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/rpc-relay
install -o root -g root -m 755 opt/farm/bin/rpc-relay /opt/farm/bin/
systemctl restart rpc-relay.service
for i in $(seq 1 20); do curl -fs -m 3 -H 'content-type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' 'http://127.0.0.1:8545/ethereum?lane=research' >/dev/null && break; sleep 1; done
q() { curl -s -m 10 -H 'content-type: application/json' --data "$1" 'http://127.0.0.1:8545/ethereum?lane=research' \
      | python3 -c 'import sys,json; r=json.load(sys.stdin)["result"]; print(int(r if isinstance(r,str) else r["number"],16))'; }
echo "blockNumber        $(q '{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}')"
echo "latest block       $(q '{"jsonrpc":"2.0","id":1,"method":"eth_getBlockByNumber","params":["latest",false]}')"
sleep 13
echo "latest after 13 s  $(q '{"jsonrpc":"2.0","id":1,"method":"eth_getBlockByNumber","params":["latest",false]}')"
echo "Installed phase 6w."
