#!/usr/bin/env bash
# Phase 10i: cut the farm's own Alchemy use on the live lane (2026-11-11).
# Measured on 2026-11-11: about 4.2M CU/day on the live lane with four live bots, of which the bots
# themselves are roughly 0.8M. The rest is the farm watching itself:
#  - farm-watchdog read balance, nonce, price and USDC of every live bot every 15 s (about 2.1M/day).
#    Now: the nonce every round (the key-compromise check is unchanged); balance, USDC and price
#    every gate.json `watchdog_balance_interval_s` (set to 60 here), at once when the nonce moved,
#    the first time, and after a failed read; the price once per feed and round. The per-interval
#    drop check (> L) and the live-loss stop (30 USD) run on the rounds that read the balance, so
#    a loss without a transaction of the bot is seen up to 60 s later than before (human decision
#    2026-11-11). Without the gate.json key the watchdog reads everything every round, as before.
#  - farm-dash ran `gate-ctl status` (all chains) every 60 s while the page was open (about
#    1.3M/day). Now cached 5 minutes for the page and data.json; brief.txt still gets data at most
#    60 s old.
# Checks run before anything changes. If farm-watchdog or farm-dash does not come back, the two
# programs and gate.json are restored. Backups: .<name>.bak-10i. Safe to re-run.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin L=/opt/farm/lib E=/etc/farm
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
export PYTHONDONTWRITEBYTECODE=1
pyc() { python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$1"; }

for f in patch-10i.py test-10i.py regress/test-10e.py regress/test-10g.py; do pyc "$f"; done
echo "== patch texts"
python3 -I -B patch-10i.py check "$B/farm-watchdog" "$B/farm-dash"
python3 -I -B patch-10i.py apply "$B/farm-watchdog" "$B/farm-dash" "$tmp" >/dev/null
pyc "$tmp/farm-watchdog"; pyc "$tmp/farm-dash"
echo "== offline tests (installed files: report only)"
python3 -I -B test-10i.py "$B/farm-watchdog" "$B/farm-dash" "$L" --old || true
echo "== offline tests (patched files)"
python3 -I -B test-10i.py "$tmp/farm-watchdog" "$tmp/farm-dash" "$L"
echo "== earlier tests against the patched watchdog (10e, 10g)"
python3 -I -B regress/test-10e.py "$B/gate-ctl" "$B/farm-signer" "$tmp/farm-watchdog" "$L" | tail -1
python3 -I -B regress/test-10g.py "$B/gate-ctl" "$B/farm-signer" "$tmp/farm-watchdog" "$L" | tail -1

echo "== Alchemy CU today, before"
curl -s --max-time 5 http://127.0.0.1:8545/health | python3 -I -c 'import json,sys; print(" ", json.load(sys.stdin).get("alchemy_cu_today"))' || true

echo "== backup"
bak() { local d f; d=$(dirname "$1"); f=$(basename "$1"); [[ -e "$d/.$f.bak-10i" ]] || cp -a "$1" "$d/.$f.bak-10i"; }
bak "$B/farm-watchdog"; bak "$B/farm-dash"; bak "$E/gate.json"
put() { install -o "$(stat -c %u "$2")" -g "$(stat -c %g "$2")" -m "$(stat -c %a "$2")" "$1" "$2"; }
rollback() {
  echo "!! $1 - restoring farm-watchdog, farm-dash and gate.json" >&2
  cp -a "$B/.farm-watchdog.bak-10i" "$B/farm-watchdog"
  cp -a "$B/.farm-dash.bak-10i" "$B/farm-dash"
  cp -a "$E/.gate.json.bak-10i" "$E/gate.json"
  systemctl restart farm-watchdog farm-dash || true
  sleep 5
  systemctl is-active farm-watchdog farm-dash || true
  journalctl -u farm-watchdog -u farm-dash -n 30 --no-pager || true
  exit 1
}

echo "== gate.json: watchdog_balance_interval_s"
python3 -I -B - "$E/gate.json" <<'PY'
import json, sys
p = sys.argv[1]
with open(p, encoding="utf-8") as f:
    c = json.load(f)
old = c.get("watchdog_balance_interval_s")
c["watchdog_balance_interval_s"] = 60
with open(p, "r+", encoding="utf-8") as f:           # in place: owner and mode stay
    f.seek(0)
    json.dump(c, f, indent=2)
    f.write("\n")
    f.truncate()
print(f"  watchdog_interval_s {c['watchdog_interval_s']} (nonce), watchdog_balance_interval_s {old} -> 60")
PY

echo "== install and restart"
since=$(date -u '+%Y-%m-%d %H:%M:%S')
put "$tmp/farm-watchdog" "$B/farm-watchdog"
put "$tmp/farm-dash" "$B/farm-dash"
systemctl restart farm-watchdog farm-dash
sleep 25                                   # one full watchdog round and the next nonce-only round
for u in farm-watchdog farm-dash; do
  systemctl is-active --quiet "$u" || rollback "$u is not active after the restart"
done
if journalctl -u farm-watchdog --since "$since" --no-pager | grep -Eq "Traceback|watchdog: (Name|Type|Unbound|Attribute|Key|Index|Value)[A-Za-z]*Error\("; then
  rollback "farm-watchdog logged an error after the restart"
fi
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 90 http://127.0.0.1:8090/data.json || true)
[[ $code == 200 ]] || rollback "farm-dash answered HTTP $code"
echo "farm-watchdog and farm-dash active, dashboard HTTP 200"
journalctl -u farm-watchdog --since "$since" --no-pager | tail -n 8
python3 -I -B patch-10i.py check "$B/farm-watchdog" "$B/farm-dash" | grep -c "already applied" | sed 's/^/  hunks in place: /'
echo "Installed phase 10i. Paste everything from '== patch texts' down."
echo "In an hour:  sudo sqlite3 /var/lib/farm/ops.db \"SELECT chain,ok,cu FROM rpc_stats WHERE day=date('now') AND lane='live' AND provider='alchemy' ORDER BY cu DESC\""
