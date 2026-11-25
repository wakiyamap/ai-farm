#!/usr/bin/env bash
# Phase 6c: meta's infra requests of 2026-11-03 (inbox/human/2026-11-03-meta-infra-requests.md).
#   1. paper-reviewer queue: next_review_at null is not "due"; bots changed since review are flagged
#   2. rpc-relay: an oversized upstream reply (>32 MiB) is returned as an error to the caller
#      instead of putting the provider on cooldown (was: 8 MiB read -> parse error -> 30 s cooldown)
#   3. ledger query --json: untruncated rows
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/rpc-relay opt/farm/bin/ledger
bash -n opt/farm/context/paper-reviewer
install -o root -g root -m 755 opt/farm/bin/rpc-relay opt/farm/bin/ledger /opt/farm/bin/
install -o root -g root -m 755 opt/farm/context/paper-reviewer /opt/farm/context/
systemctl restart rpc-relay.service
sleep 1
curl -sf -m 5 http://127.0.0.1:8545/health >/dev/null && echo "relay: ok" || { echo "relay health check failed" >&2; exit 1; }
sudo -u harness /opt/farm/bin/ledger query --json "SELECT 1 AS ok" | grep -q '"ok": 1' && echo "ledger --json: ok"
sudo -u harness /opt/farm/context/paper-reviewer paper-reviewer
echo "Installed phase 6c."
