#!/usr/bin/env bash
# Phase 10j (2026-11-11): two things found today.
#  1. Reboot: at 09:42:06Z the server was rebooted. rpc-relay was "started" before name resolution
#     worked ("Temporary failure in name resolution", then "no provider available" while it rested
#     the providers). farm-signer could not read its feeds, exited and restarted every 5 s; bot@
#     units Require= the signer, so every signer restart restarted all live bots, which failed too
#     and ran into their start limit (5 in 10 min). The watchdog woke the live-operator.
#     Fix: rpc-relay starts after network-online.target; farm-signer gets
#     ExecStartPre=/opt/farm/bin/relay-wait (waits up to 150 s until the relay answers
#     eth_blockNumber on ethereum, always exits 0). bot@ is ordered after the signer already.
#  2. fork: `fork reset elysium` mines one block after the reset (elysium head headers have no
#     excessBlobGas and anvil refused eth_call with "Excess blob gas not set.").
# The signer is restarted once to prove the new start path (the live bots restart with it, as in
# 10e and 10g). If the signer does not come back, the drop-in is removed and it is started again.
# Backups: /opt/farm/bin/.fork.bak-10j. Safe to re-run.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin S=/etc/systemd/system
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
export PYTHONDONTWRITEBYTECODE=1
pyc() { python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$1"; }

for f in patch-10j.py test-10j.py relay-wait; do pyc "$f"; done
echo "== patch texts"
python3 -I -B patch-10j.py check "$B/fork"
python3 -I -B patch-10j.py apply "$B/fork" "$tmp" >/dev/null
pyc "$tmp/fork"
echo "== offline tests (installed fork: report only)"
python3 -I -B test-10j.py "$B/fork" relay-wait --old || true
echo "== offline tests (patched fork)"
python3 -I -B test-10j.py "$tmp/fork" relay-wait

echo "== install fork and relay-wait"
[[ -e "$B/.fork.bak-10j" ]] || cp -a "$B/fork" "$B/.fork.bak-10j"
install -o "$(stat -c %u "$B/fork")" -g "$(stat -c %g "$B/fork")" -m "$(stat -c %a "$B/fork")" "$tmp/fork" "$B/fork"
install -o root -g root -m 755 relay-wait "$B/relay-wait"
runuser -u farmgate -- "$B/relay-wait" 30 ethereum

echo "== systemd drop-ins"
install -d -m 755 "$S/rpc-relay.service.d" "$S/farm-signer.service.d"
install -o root -g root -m 644 units/rpc-relay-network.conf "$S/rpc-relay.service.d/network.conf"
install -o root -g root -m 644 units/farm-signer-wait-relay.conf "$S/farm-signer.service.d/wait-relay.conf"
systemctl daemon-reload
systemctl show rpc-relay -p After | tr ' ' '\n' | { grep -c "network-online.target" || true; } | sed 's/^/  rpc-relay After=network-online.target: /'
systemctl show farm-signer -p ExecStartPre | { grep -c relay-wait || true; } | sed 's/^/  farm-signer ExecStartPre=relay-wait: /'

echo "== restart farm-signer once (the live bots restart with it)"
since=$(date -u '+%Y-%m-%d %H:%M:%S')
systemctl restart farm-signer || true
sleep 45
if ! systemctl is-active --quiet farm-signer; then
  echo "!! farm-signer is not active - removing the drop-in and starting it as before" >&2
  rm -f "$S/farm-signer.service.d/wait-relay.conf"
  systemctl daemon-reload
  systemctl restart farm-signer || true
  sleep 10
  systemctl is-active farm-signer || true
  journalctl -u farm-signer --since "$since" --no-pager | tail -n 20
  exit 1
fi
journalctl -u farm-signer --since "$since" --no-pager | { grep -E "relay-wait|listening|disabled" || true; } | tail -n 5
echo "farm-signer active. Live bots:"
for u in $(systemctl list-units --plain --no-legend --all 'bot@*.service' | awk '{print $1}'); do
  echo "  $u $(systemctl show "$u" -p ActiveState -p SubState --value | tr '\n' ' ')"
done

echo "== fork reset elysium, then an eth_call on the fresh fork (USDC decimals, expect ...06)"
if out=$(runuser -u harness -- "$B/fork" reset elysium 2>&1); then
  echo "$out" | sed 's/^/  /'
  runuser -u harness -- "$B/fork" call elysium '{"to":"0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65","data":"0x313ce567"}' 2>&1 | sed 's/^/  eth_call: /' || true
else
  echo "$out" | sed 's/^/  /'
  echo "  (reset not done - a lease or the fork service; run 'fork reset elysium' later to check)"
fi

note=/srv/farm/ws/inbox/meta/2026-11-11-phase10j-fork-elysium-boot.md
[[ -e $note ]] || install -m 664 inbox-meta-2026-11-11-phase10j-fork-elysium-boot.md "$note"
echo "Installed phase 10j. Paste everything from '== patch texts' down."
echo "If a bot above is not 'active running' a minute from now: sudo -u harness /opt/farm/bin/gate restart <id>"
