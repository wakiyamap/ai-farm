#!/usr/bin/env bash
# Phase 10l: gate-ctl, after the partial promotion of morpho-watcher2-ethereum (2026-11-11 20:39Z:
# moved to live, funded 16 USD, then "executor deployment on ethereum needs 3,190,399 gas").
#  - promote estimates the executor deployment on every chain of the bot before anything moves,
#    and refuses there when it exceeds the per-transaction gas limit or cannot be estimated.
#    Until now only hyperevm was checked up front; elsewhere deploy_executor refused after the
#    bot had been moved to live and funded
# Checks run before anything changes; no service restart (gate-ctl is read on every call). Backup:
# .gate-ctl.bak-10l. This does not touch the stranded bot: stop it with
#   sudo -u harness /opt/farm/bin/gate stop morpho-watcher2-ethereum
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
export PYTHONDONTWRITEBYTECODE=1

for f in patch-10l.py test-10l.py regress/test-10e.py regress/test-10f.py regress/test-10g.py; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$f"
done
echo "== patch texts"
python3 -I -B patch-10l.py check "$B/gate-ctl"
python3 -I -B patch-10l.py apply "$B/gate-ctl" "$tmp" >/dev/null
python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$tmp/gate-ctl"
echo "== offline tests"
python3 -I -B test-10l.py "$B/gate-ctl" /opt/farm/lib --old || true
python3 -I -B test-10l.py "$tmp/gate-ctl" /opt/farm/lib
echo "== regression (10e, 10f, 10g suites on the 10l gate-ctl)"
python3 -I -B regress/test-10e.py "$tmp/gate-ctl" "$B/farm-signer" "$B/farm-watchdog" /opt/farm/lib | tail -1
python3 -I -B regress/test-10f.py "$tmp/gate-ctl" /opt/farm/lib | tail -1
python3 -I -B regress/test-10g.py "$tmp/gate-ctl" "$B/farm-signer" "$B/farm-watchdog" /opt/farm/lib | tail -1

echo "== backup"
[[ -e "$B/.gate-ctl.bak-10l" ]] || cp -a "$B/gate-ctl" "$B/.gate-ctl.bak-10l"
echo "== install"
install -o "$(stat -c %u "$B/gate-ctl")" -g "$(stat -c %g "$B/gate-ctl")" -m "$(stat -c %a "$B/gate-ctl")" "$tmp/gate-ctl" "$B/gate-ctl"
if ! sudo -u harness /opt/farm/bin/gate status > "$tmp/status.out"; then
  echo "!! gate status failed - restoring the pre-10l gate-ctl" >&2
  cp -a "$B/.gate-ctl.bak-10l" "$B/gate-ctl"
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
echo "Installed phase 10l. Paste everything from '== patch texts' down."
