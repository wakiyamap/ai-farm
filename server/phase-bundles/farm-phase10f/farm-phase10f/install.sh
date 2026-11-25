#!/usr/bin/env bash
# Phase 10f: gate-ctl, after the partial promotion of reserve-dutch-ethereum-v2 (2026-11-10 20:05Z:
# moved to live, funded 30 USD, then "executor artifact unreadable").
#  - the manifest's executor path pointed into the bot's own paper directory
#    (bots/paper/<id>/contracts/...); promote moves that directory to bots/live/<id>/ first and read
#    the artifact afterwards, so the path no longer existed. executor_code() now finds such an
#    artifact under bots/live/<id>/ after the move
#  - promote reads the artifact and executor_args before anything moves, so an unreadable artifact
#    refuses before the move and the funding, on every chain
#  - a state/executor.json that this bot's key did not produce (copied in from an archived live bot)
#    no longer counts as "already has an executor" for `gate-ctl deploy`, and is removed before the
#    deployment is sent (the signer would otherwise allow that foreign address)
# Checks run before anything changes; no service restart (gate-ctl is read on every call). Backup:
# .gate-ctl.bak-10f. This does NOT deploy: finish the stranded bot with
#   sudo -u farmgate /opt/farm/bin/gate-ctl deploy reserve-dutch-ethereum-v2
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
export PYTHONDONTWRITEBYTECODE=1

for f in patch-10f.py test-10f.py regress/test-10e.py; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$f"
done
echo "== patch texts"
python3 -I -B patch-10f.py check "$B/gate-ctl"
python3 -I -B patch-10f.py apply "$B/gate-ctl" "$tmp" >/dev/null
python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$tmp/gate-ctl"
echo "== offline tests"
python3 -I -B test-10f.py "$B/gate-ctl" /opt/farm/lib --old || true
python3 -I -B test-10f.py "$tmp/gate-ctl" /opt/farm/lib
echo "== regression (10e suite on the 10f gate-ctl)"
python3 -I -B regress/test-10e.py "$tmp/gate-ctl" "$B/farm-signer" "$B/farm-watchdog" /opt/farm/lib | tail -1

echo "== backup"
[[ -e "$B/.gate-ctl.bak-10f" ]] || cp -a "$B/gate-ctl" "$B/.gate-ctl.bak-10f"
echo "== install"
install -o "$(stat -c %u "$B/gate-ctl")" -g "$(stat -c %g "$B/gate-ctl")" -m "$(stat -c %a "$B/gate-ctl")" "$tmp/gate-ctl" "$B/gate-ctl"
if ! sudo -u harness /opt/farm/bin/gate status > "$tmp/status.out"; then
  echo "!! gate status failed - restoring the pre-10f gate-ctl" >&2
  cp -a "$B/.gate-ctl.bak-10f" "$B/gate-ctl"
  exit 1
fi
python3 -I -B - "$tmp/status.out" <<'EOF' || cat "$tmp/status.out"
import json, sys
s = json.load(open(sys.argv[1]))
print("capital_usd", s.get("capital_usd"), "/", s.get("max_capital_usd"), " daily_loss_usd", s.get("daily_loss_usd"),
      " frozen", s.get("frozen"), " halted", s.get("halted"))
for b, v in sorted((s.get("live") or {}).items()):
    print(f"  {b}: {v.get('service')}  {v.get('balances_usd')}")
EOF
echo "Installed phase 10f. Paste everything from '== patch texts' down."
