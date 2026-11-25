#!/usr/bin/env bash
# Phase 6y (inbox/human/2026-11-08-meta-relay-*.md, 2026-11-08-meta-relay-state-1inch-paperctl.md §1/§3):
#  - rpc-relay: an empty-looking answer from a public node (getCode/eth_call "0x", null receipt) is
#    checked with the next provider (Alchemy) before it is trusted; if that answers non-empty the
#    public node is cooled down 5 min. Such empties are never cached (the cache is shared by all
#    lanes, so one bad public answer could reach the live lane). A public-node error other than a
#    revert (-32602 Variadic / string length, "specify an address", range caps) falls through to
#    the next provider instead of failing the call.
#  - paper-ctl: start/restart state check parsed `systemctl show --value` positionally, but systemctl
#    prints properties in its own order -> false "failed ... result running". Now parses key=value.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/rpc-relay opt/farm/bin/paper-ctl
install -o root -g root -m 755 opt/farm/bin/rpc-relay opt/farm/bin/paper-ctl /opt/farm/bin/
systemctl restart rpc-relay.service
sleep 2
echo "== meta's getCode check: checksummed addresses, in one JSON-RPC batch with USDC (research lane)"
curl -s -m 30 -H 'content-type: application/json' 'http://127.0.0.1:8545/ethereum?lane=research' --data '[
 {"jsonrpc":"2.0","id":1,"method":"eth_getCode","params":["0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48","latest"]},
 {"jsonrpc":"2.0","id":2,"method":"eth_getCode","params":["0x87870Bca3F3fD6335C3F4f8307Fcf24007E6eF5b","latest"]},
 {"jsonrpc":"2.0","id":3,"method":"eth_getCode","params":["0x1F98430969A57124529677A665539560880E4AeF","latest"]},
 {"jsonrpc":"2.0","id":4,"method":"eth_getCode","params":["0x5C69bEe701ef98a540404BdE40a2A6B6A7f4697f","latest"]},
 {"jsonrpc":"2.0","id":5,"method":"eth_getCode","params":["0x7a250d5630B4CF0795886e19A6bE22F2e0721B9c","latest"]}]' \
 | python3 -c 'import sys,json; d=json.load(sys.stdin); d=d if isinstance(d,list) else [d]
for x in d: print(x.get("id"), (x.get("result") or "")[:12], "len", len(x.get("result") or ""), x.get("error",""))'
echo "Installed phase 6y."
