#!/usr/bin/env bash
# Phase 6m: reviewer-only ethereum fork + lease history (inbox/human/2026-11-05-meta-reviewer-fork.md).
#   - fork@ethereum-review.service on 127.0.0.1:9013 (chain id 1, upstream ethereum), reachable by
#     harness (reviewer/meta/researcher) only: nftables keeps the earner and the bots off it
#   - fork@.service takes the upstream chain from FORK_UPSTREAM in fork-<instance>.env
#   - fork CLI knows "ethereum-review"; lease/release/force are appended to scratch/.fork/<chain>.lease.log
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/fork
for c in base arbitrum ethereum; do
  grep -q '^FORK_UPSTREAM=' "/etc/farm/fork-$c.env" || echo "FORK_UPSTREAM=$c" >> "/etc/farm/fork-$c.env"
done
install -o root -g root -m 644 etc/farm/fork-ethereum-review.env etc/farm/farm.nft /etc/farm/
install -o root -g root -m 644 etc/systemd/system/fork@.service /etc/systemd/system/
install -o root -g root -m 755 opt/farm/bin/fork /opt/farm/bin/
systemctl daemon-reload
systemctl restart farm-nft.service
systemctl enable --now fork@ethereum-review.service
# the three existing forks keep running on the old unit text until restarted; restart them one at a
# time only when free (a restart wipes fork state like a reset)
for c in base arbitrum ethereum; do
  if [[ -f "/srv/farm/ws/scratch/.fork/$c.lease" ]] && python3 -c "import json,sys,time; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get('until',0)>time.time() else 1)" "/srv/farm/ws/scratch/.fork/$c.lease"; then
    echo "fork@$c is leased; not restarting it now (it picks up the new unit on its next restart)"
  else
    systemctl restart "fork@$c.service"
  fi
done
for i in $(seq 1 30); do
  curl -s -m 3 -X POST http://127.0.0.1:9013 -H 'content-type: application/json' \
    -d '{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}' | grep -q result && break
  sleep 2
done
sudo -u harness /opt/farm/bin/fork status
echo "earner reachability check (must fail):"
sudo -u earner curl -s -m 3 http://127.0.0.1:9013 >/dev/null && echo "WARNING: earner can reach 9013" || echo "ok: earner cannot reach 9013"
echo "Installed phase 6m."
