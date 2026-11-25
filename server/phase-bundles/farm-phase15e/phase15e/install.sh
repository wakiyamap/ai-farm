#!/usr/bin/env bash
# Phase 15e (2026-11-18): the watchdog off the live lane.
#  The watchdog read every live bot every 15 s on the live lane (Alchemy first, no budget), about
#  180k CU a day per bot. With 23 live bots the live lane used 882k CU by 03:35 UTC (about 6M a day)
#  and the Alchemy cycle was on course to run out before 12-01, which stops every send.
#  - rpc-relay (2 text patches): lane `watch` (public first, Alchemy fallback within its budget);
#    /health cycle also projects from the recent pace (pace_cu_per_day, projected_cu_recent) and
#    alert_85 uses the higher projection
#  - farm-watchdog (1 text patch): reads through lane `watch`. Checks and intervals unchanged.
#  - relay.json: alchemy_daily_cu.watch 300000; fork 400000 -> 600000
#  rpc-relay and farm-watchdog are restarted. If either does not come back, both programs and
#  relay.json are restored.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
RJ=/etc/farm/relay.json
export PYTHONDONTWRITEBYTECODE=1
sha() { sha256sum "$1" | cut -d' ' -f1; }
RELAY_15C=323337d8ffe6a46a7ca759101b1f8c823521332a5f990c2448d075fe9581006c
WD_12D=4f692e414c9825168d879e15e4455725536038d48946d02bce5e8fcbe5ea13f9
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
health() { curl -s -m 5 http://127.0.0.1:8545/health; }

echo "== checks (nothing is changed yet)"
for f in patch-15e.py test-15e.py cfg-15e.py; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$f"
done
hr=$(sha $B/rpc-relay); hw=$(sha $B/farm-watchdog)
echo "  sha256 now (reference / installed)"
echo "    rpc-relay     $RELAY_15C (15c)"
echo "                  $hr"
echo "    farm-watchdog $WD_12D (12d)"
echo "                  $hw"
if grep -q '"watch")' $B/rpc-relay && grep -q '?lane=watch"' $B/farm-watchdog; then
  echo "  already the 15e versions"; cp $B/rpc-relay $B/farm-watchdog "$tmp/"; NEWFILES=0
else
  [[ $hr == "$RELAY_15C" ]] || echo "  note: rpc-relay differs from the 15c version; the text patches decide"
  [[ $hw == "$WD_12D" ]] || echo "  note: farm-watchdog differs from the 12d version; the text patch decides"
  python3 -I -B patch-15e.py check $B/rpc-relay $B/farm-watchdog
  python3 -I -B patch-15e.py apply $B/rpc-relay $B/farm-watchdog "$tmp"
  for f in rpc-relay farm-watchdog; do
    python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$tmp/$f"
  done
  NEWFILES=1
fi
echo "  relay.json now:"; python3 -I -B cfg-15e.py show $RJ
python3 -I -B cfg-15e.py apply $RJ "$tmp/relay.json" > /dev/null
echo "== offline tests (installed files: report only, 1 of 5 before 15e)"
python3 -I -B test-15e.py $B/rpc-relay $B/farm-watchdog --old | tail -1
echo "== offline tests (patched files)"
python3 -I -B test-15e.py "$tmp/rpc-relay" "$tmp/farm-watchdog"
echo "== regression: the 15c tests on the patched relay"
python3 -I -B regress-15c.py "$tmp/rpc-relay" $B/farm-hermes | tail -1

back() {
  echo "!! $1 - restoring rpc-relay, farm-watchdog and relay.json" >&2
  [[ -f $B/.rpc-relay.bak-15e ]] && cp -a $B/.rpc-relay.bak-15e $B/rpc-relay
  [[ -f $B/.farm-watchdog.bak-15e ]] && cp -a $B/.farm-watchdog.bak-15e $B/farm-watchdog
  [[ -f $RJ.bak-15e ]] && cat "$RJ.bak-15e" > $RJ
  systemctl restart rpc-relay.service || true
  sleep 5
  systemctl restart farm-watchdog.service || true
  sleep 5
  systemctl is-active rpc-relay.service farm-watchdog.service farm-signer.service || true
  journalctl -u farm-watchdog -n 15 --no-pager >&2 || true
  exit 1
}

live0=$(health | python3 -I -c 'import json,sys; print(json.load(sys.stdin)["alchemy_cu_today"]["live"])')
echo "== install"
[[ -e $B/.rpc-relay.bak-15e ]] || cp -a $B/rpc-relay $B/.rpc-relay.bak-15e
[[ -e $B/.farm-watchdog.bak-15e ]] || cp -a $B/farm-watchdog $B/.farm-watchdog.bak-15e
[[ -e $RJ.bak-15e ]] || cp -a $RJ $RJ.bak-15e
put() { install -o "$(stat -c %u "$2")" -g "$(stat -c %g "$2")" -m "$(stat -c %a "$2")" "$1" "$2"; }
put "$tmp/rpc-relay" $B/rpc-relay
put "$tmp/farm-watchdog" $B/farm-watchdog
cat "$tmp/relay.json" > $RJ
systemctl restart rpc-relay.service
ok=0
for _ in $(seq 1 20); do
  if health | python3 -I -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("ok") and "watch" in d["alchemy_cu_today"] and "pace_cu_per_day" in d["cycle"] else 1)' 2>/dev/null; then ok=1; break; fi
  sleep 1
done
(( ok )) || back "rpc-relay does not answer /health with the watch lane"
since=$(date '+%Y-%m-%d %H:%M:%S')
systemctl restart farm-watchdog.service
sleep 45                                     # three watchdog rounds
systemctl is-active --quiet farm-watchdog.service || back "farm-watchdog is not active after the restart"
systemctl is-active rpc-relay.service farm-signer.service farm-feed.service farm-watchdog.service
echo "  farm-watchdog journal since the restart:"
journalctl -u farm-watchdog --since "$since" --no-pager | tail -n 8 | sed 's/^/    /'
fails=$(journalctl -u farm-watchdog --since "$since" --no-pager | grep -c 'read failed' || true)
echo "  'read failed' lines since the restart: $fails (a few on public nodes are tolerated; they are retried)"
health | python3 -I -c '
import json, sys
d = json.load(sys.stdin)
s, c = d["alchemy_cu_today"], d["cycle"]
print("  alchemy CU today", json.dumps(s))
print("  budget", json.dumps(d["budget"]))
print("  cycle cu", c.get("cu"), " projected (cycle average)", c.get("projected_cu"),
      " pace/day", c.get("pace_cu_per_day"), " projected (recent pace)", c.get("projected_cu_recent"),
      " share", c.get("projected_share"), " alert_85", c.get("alert_85"))'
live1=$(health | python3 -I -c 'import json,sys; print(json.load(sys.stdin)["alchemy_cu_today"]["live"])')
echo "  live lane during the ~60 s of the install: +$(( live1 - live0 )) CU (before 15e about 4,000 CU a minute)"

echo "== sha256 (expected = patched copy checked above / installed)"
echo "  rpc-relay     $(sha "$tmp/rpc-relay")"
echo "                $(sha $B/rpc-relay)"
echo "  farm-watchdog $(sha "$tmp/farm-watchdog")"
echo "                $(sha $B/farm-watchdog)"
echo "  relay.json    $(sha "$tmp/relay.json")"
echo "                $(sha $RJ)"
echo "Installed phase 15e. Check the live lane in the next brief: it should grow by about 1-1.5M CU a day."
echo "To undo: restore $B/.rpc-relay.bak-15e, $B/.farm-watchdog.bak-15e and $RJ.bak-15e, restart rpc-relay then farm-watchdog"
