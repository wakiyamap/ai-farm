#!/usr/bin/env bash
# Phase 10e (code audit of 2026-11-11): fixes in gate-ctl, farm-signer and farm-watchdog.
#  gate-ctl
#   - promote: an executor bot whose code reads neither EXECUTOR_ADDR nor state/executor.json is
#     refused before any funds move (11-10: reserve-dutch read EXEC_ADDRESS, restart-looped, 5 USD)
#   - promote / fund: pnl.json is saved after every funding transfer (a failure on a later chain
#     left a funded bot without a baseline: no live-loss stop, no PnL at sweep)
#   - fund: wallet + top-up may not pass max_capital_per_bot_usd (only promote checked the cap)
#   - sweep: bookings survive a failure on a later chain (the next sweep read the emptied wallet as
#     "principal gone"); a transfer whose send call failed is logged with its nonce and remembered,
#     and booked as returned when it turns out to have been mined; an emptied gas wallet is booked
#     as a loss (it left no PnL record at all); every error type is caught, not only RuntimeError
#   - stop: a bot whose sweep is incomplete is no longer archived (its funds dropped out of X and
#     out of the watchdog's view, and nothing retried); exit code 3, run `gate stop <id>` again
#  farm-signer
#   - increaseAllowance is held to the approve rule (allowed spender, finite amount)
#   - every broadcast failure (socket timeout too) leaves a broadcast_failed record with the nonce
#  farm-watchdog
#   - nonces in the signer's broadcast_failed and the gate's sweep_failed / cancel_failed records
#     are known transactions, not a key compromise (a relay timeout on a transaction that was
#     mined would have halted and swept every live bot)
#   - a live-loss stop that does not finish is tried again every 10 min (it was tried once)
#   - a bot promoted again under an id the live-loss stop had stopped is judged again
#   - one unreadable directory in bots/live no longer ends the round for the bots after it
# Checks (patch texts, offline tests on the installed and on the patched files) run before anything
# changes. If farm-signer or farm-watchdog does not come back, or gate status fails, the three
# programs are restored and restarted. Backups: .<name>.bak-10e. The regression suites of earlier
# phases are not re-run: several of their fixtures promote an executor bot that has no code at all,
# which 10e refuses on purpose; test-10e.py covers promote, fund, sweep, stop and the watchdog loop.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
INST=("$B/gate-ctl" "$B/farm-signer" "$B/farm-watchdog")
export PYTHONDONTWRITEBYTECODE=1

python3 -I -B -m py_compile patch-10e.py test-10e.py
rm -rf __pycache__
echo "== patch texts"
python3 -I -B patch-10e.py check "${INST[@]}"
python3 -I -B patch-10e.py apply "${INST[@]}" "$tmp" >/dev/null
for f in gate-ctl farm-signer farm-watchdog; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$tmp/$f"
done
echo "== offline tests"
python3 -I -B test-10e.py "${INST[@]}" /opt/farm/lib --old || true
python3 -I -B test-10e.py "$tmp/gate-ctl" "$tmp/farm-signer" "$tmp/farm-watchdog" /opt/farm/lib

echo "== backups"
bak() { local d f; d=$(dirname "$1"); f=$(basename "$1"); [[ -e "$d/.$f.bak-10e" ]] || cp -a "$1" "$d/.$f.bak-10e"; }
for f in "${INST[@]}"; do bak "$f"; done

rollback() {
  echo "!! $1 - restoring the pre-10e programs" >&2
  for f in gate-ctl farm-signer farm-watchdog; do cp -a "$B/.$f.bak-10e" "$B/$f"; done
  systemctl restart farm-signer farm-watchdog || true
  sleep 5
  systemctl is-active farm-signer farm-watchdog || true
  journalctl -u farm-signer -u farm-watchdog -n 30 --no-pager || true
  exit 1
}

echo "== install"
put() { install -o "$(stat -c %u "$2")" -g "$(stat -c %g "$2")" -m "$(stat -c %a "$2")" "$1" "$2"; }
put "$tmp/gate-ctl" "$B/gate-ctl"
put "$tmp/farm-signer" "$B/farm-signer"
put "$tmp/farm-watchdog" "$B/farm-watchdog"
since=$(date '+%Y-%m-%d %H:%M:%S')
systemctl restart farm-signer farm-watchdog
sleep 25                                   # the signer's feed check and one full watchdog round (15 s)
for u in farm-signer farm-watchdog; do
  systemctl is-active --quiet "$u" || rollback "$u is not active after the restart"
done
echo "farm-signer and farm-watchdog active"
journalctl -u farm-signer -u farm-watchdog --since "$since" --no-pager | tail -n 15
grep -h '"chain_disabled"' /var/lib/farmgate/signer.log 2>/dev/null | tail -n 3 || true

echo "== gate status"
sudo -u harness /opt/farm/bin/gate status > "$tmp/status.out" || rollback "gate status failed"
python3 -I -B - "$tmp/status.out" <<'EOF' || cat "$tmp/status.out"
import json, sys
s = json.load(open(sys.argv[1]))
print("capital_usd", s.get("capital_usd"), "/", s.get("max_capital_usd"), " daily_loss_usd", s.get("daily_loss_usd"),
      " frozen", s.get("frozen"), " halted", s.get("halted"))
for b, v in sorted((s.get("live") or {}).items()):
    print(f"  {b}: {v.get('service')}  {v.get('balances_usd')}")
EOF

note=/srv/farm/ws/inbox/meta/2026-11-11-phase10e-gate-watchdog.md
[[ -e $note ]] || install -m 664 inbox-meta-2026-11-11-phase10e-gate-watchdog.md "$note"
ls -la "$note"
echo "Installed phase 10e. Paste everything from '== patch texts' down."
