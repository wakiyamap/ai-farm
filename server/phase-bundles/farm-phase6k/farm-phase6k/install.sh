#!/usr/bin/env bash
# Phase 6k: meta proposal 2026-11-04 (run bfec56e0) §2 §3 + relay archive routing.
#   - fork: lease/release + generation counter; reset/replay refuse while another run holds a lease
#   - rpc-relay: reads pinned to blocks older than head-800 go to Alchemy first (public nodes have no archive)
#   - record-run: after every run, commit prompts/roles, common.md and ws/tools into ws/history (git)
#   - run-role: meta may read git log/show/diff of ws/history and ws/wiki
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/fork opt/farm/bin/rpc-relay opt/farm/bin/record-run
bash -n opt/farm/bin/run-role
command -v rsync >/dev/null || apt-get install -y rsync >/dev/null
install -o root -g root -m 755 opt/farm/bin/fork opt/farm/bin/rpc-relay opt/farm/bin/record-run opt/farm/bin/run-role /opt/farm/bin/
WS=/srv/farm/ws
install -d -o root -g farm -m 2775 "$WS/scratch/.fork"
setfacl -m d:g:farm:rwX -m d:m::rwx "$WS/scratch/.fork"
if [[ ! -d "$WS/history/.git" ]]; then
  install -d -o root -g farm -m 2755 "$WS/history"
  git -C "$WS/history" init -q
  git -C "$WS/history" -c user.name=farm-harness -c user.email=farm@localhost commit -q --allow-empty -m "history start"
fi
chmod -R g+rX "$WS/history"
# git refuses repos owned by another user ("dubious ownership"); root writes it, harness reads it
git config --system --add safe.directory "$WS/history" 2>/dev/null || true
git config --system --add safe.directory "$WS/wiki" 2>/dev/null || true
systemctl restart rpc-relay.service
sleep 1
curl -sf -m 5 http://127.0.0.1:8545/health >/dev/null && echo "relay: ok"
sudo -u earner /opt/farm/bin/fork status
# first snapshot now, so meta's next run already has a baseline commit
INVOCATION_ID=install-6k SERVICE_RESULT=install /opt/farm/bin/record-run meta >/dev/null 2>&1 || true
git -C "$WS/history" log --oneline | head -3
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  /opt/farm/bin/assemble-prompt "$inst"
done < /etc/farm/roles.conf
echo "Installed phase 6k."
