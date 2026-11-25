#!/usr/bin/env bash
# Phase 9f = phase 9e + the promote funding race:
#  - gate promote sent the bot's gas funding and deployed the executor immediately, before the
#    funding tx was mined -> "insufficient funds ... have 0" and a funded live bot without an
#    executor (franken-dutch, gearbox-v3 on 2026-11-09). The gate now waits for the funding receipts.
#  - new `gate-ctl deploy <id>`: finish such a half-done promotion (deploy executor, start service).
# Includes everything of 9e (manifest parsing, executor_args + {bot}, deploy receipt check, ledger
# fair share). Safe to re-run; does NOT deploy or start anything by itself.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/gate-ctl opt/farm/bin/farm-signer opt/farm/bin/ledger-ingest
for f in gate-ctl farm-signer ledger-ingest; do cp -a "/opt/farm/bin/$f" "/opt/farm/bin/.$f.bak-9f"; done
install -o root -g root -m 755 opt/farm/bin/gate-ctl opt/farm/bin/farm-signer opt/farm/bin/ledger-ingest /opt/farm/bin/
systemctl restart farm-signer.service
sleep 3
systemctl is-active farm-signer.service
echo "== half-promoted live bots (no state/executor.json) and their constructor args"
for d in /srv/farm/ws/bots/live/*/; do
  id=$(basename "$d")
  [[ -f "$d/state/executor.json" ]] && continue
  echo "-- $id  service=$(systemctl is-active "bot@$id.service" 2>/dev/null || true)"
  grep -E '^(executor|executor_args):' "$d/manifest.yaml" | cut -c1-200
  grep -q '{bot}' "$d/manifest.yaml" && echo "   executor_args uses {bot}" || echo "   executor_args has NO {bot} placeholder"
done
echo "Installed phase 9f."
