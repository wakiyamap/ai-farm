#!/usr/bin/env bash
# Phase 6j: eth_sendRawTransaction goes to Alchemy only (no public-node fallback for broadcasts).
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/rpc-relay
grep -q '"alchemy_key"\|alchemy' /etc/farm/relay.json || { echo "relay.json has no Alchemy key; sends would always fail" >&2; exit 1; }
install -o root -g root -m 755 opt/farm/bin/rpc-relay /opt/farm/bin/
systemctl restart rpc-relay.service
sleep 1
curl -sf -m 5 http://127.0.0.1:8545/health >/dev/null && echo "relay: ok"
echo "Installed phase 6j."
