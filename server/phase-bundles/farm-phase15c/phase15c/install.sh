#!/usr/bin/env bash
# Phase 15c (2026-11-18, human decisions on meta's report of 11-17 21:45Z):
#  - rpc-relay (7 text patches) + relay.json: lanes `fork` (user farmfork, 400k CU/day, Alchemy first)
#    and `scout` (user earner, 300k CU/day, public first), chosen by the connecting unix user;
#    research 1.0M -> 700k. GET /health gains `cycle` (Alchemy billing cycle projection, alert_85),
#    GET /lane shows the lane of a connection. rpc-relay is restarted.
#  - farm-hermes (new service, 127.0.0.1:29486): Pyth Hermes with the human's key (Authorization:
#    Bearer). Skipped, with instructions, when /etc/farm/pyth-hermes.key does not exist yet.
#  - farm-paper-reviewer-claude.timer: every 24 h instead of 90 min (drop-in daily.conf)
#  - decisions/human/2026-11-18-lanes-hermes-toga.md and a note for meta
# BEFORE running, put the Pyth key in place (it is never printed):
#     sudo install -o root -g root -m 600 /dev/stdin /etc/farm/pyth-hermes.key   # paste, Enter, Ctrl-D
# If the relay does not come back or the lanes are not assigned as intended, rpc-relay and
# relay.json are restored. If Hermes refuses the key, only farm-hermes is stopped.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
RJ=/etc/farm/relay.json
KEYFILE=/etc/farm/pyth-hermes.key
HCONF=/etc/farm/hermes.json
HUNIT=/etc/systemd/system/farm-hermes.service
TDIR=/etc/systemd/system/farm-paper-reviewer-claude.timer.d
WS=/srv/farm/ws
PORT=29486
export PYTHONDONTWRITEBYTECODE=1
sha() { sha256sum "$1" | cut -d' ' -f1; }
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "== checks (nothing is changed yet)"
for f in patch-15c.py test-15c.py cfg-15c.py farm-hermes; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$f"
done
python3 -I -B -c 'import json,sys; json.load(open(sys.argv[1]))' hermes.json
echo "  rpc-relay now: $(sha $B/rpc-relay)"
if grep -q 'def mapped_lane' $B/rpc-relay; then
  echo "  rpc-relay is already the 15c version"
  cp $B/rpc-relay "$tmp/rpc-relay"; RELAY_NEW=0
else
  python3 -I -B patch-15c.py check $B/rpc-relay
  python3 -I -B patch-15c.py apply $B/rpc-relay "$tmp"
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$tmp/rpc-relay"
  RELAY_NEW=1
fi
echo "  relay.json now:"; python3 -I -B cfg-15c.py show $RJ
python3 -I -B cfg-15c.py apply $RJ "$tmp/relay.json" > /dev/null
echo "== offline tests (installed relay: report only)"
python3 -I -B test-15c.py $B/rpc-relay farm-hermes --old | tail -1
echo "== offline tests (patched relay)"
python3 -I -B test-15c.py "$tmp/rpc-relay" farm-hermes
HERMES=1
if [[ ! -s $KEYFILE ]]; then
  HERMES=0
  echo "  $KEYFILE is missing: farm-hermes is skipped this time. Create it, then run this again:"
  echo "    sudo install -o root -g root -m 600 /dev/stdin $KEYFILE    # paste the key, Enter, Ctrl-D"
else
  [[ $(stat -c '%U:%G %a' $KEYFILE) == "root:root 600" ]] || { chown root:root $KEYFILE; chmod 600 $KEYFILE; echo "  $KEYFILE: set to root:root 600"; }
  python3 -I -B - $KEYFILE <<'PY' || { echo "  $KEYFILE does not look like one API key (one line, no spaces, 8-400 chars). Nothing was changed." >&2; exit 1; }
import re, sys
sys.exit(0 if re.fullmatch(r"[\x21-\x7e]{8,400}", open(sys.argv[1], encoding="utf-8").read().strip()) else 1)
PY
  echo "  $KEYFILE: present, root 600, $(tr -d '\n\r ' < $KEYFILE | wc -c) characters"
  if ! systemctl is-active --quiet farm-hermes.service && ss -ltnH "sport = :$PORT" | grep -q .; then
    echo "  port $PORT is already in use by something else. Nothing was changed." >&2; exit 1
  fi
fi

lane_of() {   # lane_of <user>: the lane the relay gives this user for lane=research
  runuser -u "$1" -- python3 -I -c 'import json,urllib.request; print(json.loads(urllib.request.urlopen("http://127.0.0.1:8545/lane?lane=research", timeout=5).read())["lane"])' 2>/dev/null || echo "?"
}
relay_back() {
  echo "!! $1 - restoring rpc-relay and relay.json" >&2
  [[ -f $B/.rpc-relay.bak-15c ]] && cp -a $B/.rpc-relay.bak-15c $B/rpc-relay
  [[ -f $RJ.bak-15c ]] && cat "$RJ.bak-15c" > $RJ
  systemctl restart rpc-relay.service || true
  sleep 5
  systemctl is-active rpc-relay.service farm-signer.service || true
  journalctl -u rpc-relay -n 15 --no-pager >&2 || true
  exit 1
}

echo "== rpc-relay and relay.json"
[[ -e $B/.rpc-relay.bak-15c ]] || cp -a $B/rpc-relay $B/.rpc-relay.bak-15c
[[ -e $RJ.bak-15c ]] || cp -a $RJ $RJ.bak-15c
install -o "$(stat -c %u $B/rpc-relay)" -g "$(stat -c %g $B/rpc-relay)" -m "$(stat -c %a $B/rpc-relay)" "$tmp/rpc-relay" $B/rpc-relay
cat "$tmp/relay.json" > $RJ                  # keeps owner and mode
systemctl restart rpc-relay.service
ok=0
for _ in $(seq 1 20); do
  if curl -s -m 3 http://127.0.0.1:8545/health | python3 -I -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("ok") and "cycle" in d else 1)' 2>/dev/null; then ok=1; break; fi
  sleep 1
done
(( ok )) || relay_back "rpc-relay does not answer /health with the cycle"
curl -s -m 5 http://127.0.0.1:8545/health | python3 -I -c '
import json, sys
d = json.load(sys.stdin)
print("  budget", json.dumps(d["budget"]))
c = d["cycle"]
print("  cycle", c.get("since"), "->", c.get("ends"), " cu", c.get("cu"), " projected", c.get("projected_cu"),
      " share", c.get("projected_share"), " alert_85", c.get("alert_85"))'
le=$(lane_of earner); lf=$(lane_of farmfork); lh=$(lane_of harness)
echo "  lane for lane=research: earner -> $le, farmfork -> $lf, harness -> $lh"
[[ $le == scout && $lf == fork && $lh == research ]] || relay_back "the lanes are not assigned as intended"
sleep 8
systemctl is-active rpc-relay.service farm-signer.service farm-watchdog.service farm-feed.service \
  || relay_back "a service is not active after the relay restart"
for f in $(systemctl list-units --plain --no-legend --state=active 'fork@*.service' | awk '{print $1}'); do echo "  $f active"; done

if (( HERMES )); then
  echo "== farm-hermes"
  hermes_off() {
    echo "!! $1 - stopping farm-hermes (the relay change stays)" >&2
    systemctl disable --now farm-hermes.service 2>/dev/null || true
    journalctl -u farm-hermes -n 10 --no-pager >&2 || true
    HERMES=0
  }
  [[ -e $HCONF ]] || install -o root -g root -m 644 hermes.json $HCONF
  install -o root -g root -m 755 farm-hermes $B/
  install -o root -g root -m 644 units/farm-hermes.service $HUNIT
  systemctl daemon-reload
  systemctl enable farm-hermes.service >/dev/null 2>&1 || true
  systemctl restart farm-hermes.service
  ok=0
  for _ in $(seq 1 20); do
    if curl -s -m 3 "http://127.0.0.1:$PORT/health" | grep -q '"ok": *true'; then ok=1; break; fi
    sleep 1
  done
  if (( ok )); then
    ETH=0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace
    c=$(curl -g -s -m 20 -o "$tmp/h" -w '%{http_code}' "http://127.0.0.1:$PORT/v2/updates/price/latest?ids[]=$ETH" || true)
    echo "  GET /v2/updates/price/latest (ETH/USD): HTTP $c ($(stat -c %s "$tmp/h") bytes)"
    case $c in
      200) python3 -I -c '
import json, sys
d = json.load(open(sys.argv[1]))
p = d["parsed"][0]["price"]
print("  the key is accepted: ETH/USD", int(p["price"]) * 10 ** int(p["expo"]), " binary update", len(d["binary"]["data"][0]) // 2, "bytes")' "$tmp/h" || true ;;
      401|403) head -c 300 "$tmp/h" >&2; echo >&2; hermes_off "Hermes rejected the key (HTTP $c)" ;;
      *) echo "  !! not 200 and not a key refusal; the service stays. First bytes:"; head -c 300 "$tmp/h" | sed 's/^/     /'; echo ;;
    esac
    if (( HERMES )); then
      c=$(curl -g -s -m 5 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/v2/updates/price/stream?ids[]=$ETH" || true)
      echo "  GET /v2/updates/price/stream: HTTP $c (expected 403: refused here)"
      if journalctl -u farm-hermes --no-pager -n 200 2>/dev/null \
           | python3 -I -c 'import sys; k = open(sys.argv[1]).read().strip(); sys.exit(0 if k and k in sys.stdin.read() else 1)' $KEYFILE; then
        hermes_off "the key appears in the service's journal"
      else
        echo "  the key does not appear in the service's journal"
      fi
      for u in earner harness farmbot; do
        if runuser -u $u -- python3 -I -c "import socket; socket.create_connection(('127.0.0.1', $PORT), 3)" 2>/dev/null; then
          echo "  $u: reaches farm-hermes"
        else
          echo "  $u: cannot reach port $PORT"
        fi
      done
    fi
  else
    hermes_off "farm-hermes does not answer on 127.0.0.1:$PORT"
  fi
fi

echo "== paper-reviewer-claude: every 24 h"
install -d -m 755 $TDIR
install -o root -g root -m 644 units/paper-reviewer-claude-daily.conf $TDIR/daily.conf
systemctl daemon-reload
systemctl list-timers --no-legend farm-paper-reviewer-claude.timer | sed 's/^/  /'

echo "== decision and note for meta"
install -o root -g root -m 644 decision-2026-11-18-lanes-hermes-toga.md $WS/decisions/human/2026-11-18-lanes-hermes-toga.md
install -o root -g root -m 644 inbox-meta-2026-11-18-phase15c-lanes-hermes.md $WS/inbox/meta/2026-11-18-phase15c-lanes-hermes.md

echo "== sha256 (expected = patched copy checked above / installed)"
echo "  rpc-relay   $(sha "$tmp/rpc-relay")"
echo "              $(sha $B/rpc-relay)"
echo "  relay.json  $(sha "$tmp/relay.json")"
echo "              $(sha $RJ)"
if (( HERMES )); then
  echo "  farm-hermes $(sha farm-hermes)"
  echo "              $(sha $B/farm-hermes)"
fi
echo "Installed phase 15c$( (( HERMES )) || echo ' (without farm-hermes)')."
echo "To undo: restore $B/.rpc-relay.bak-15c and $RJ.bak-15c, restart rpc-relay; systemctl disable --now farm-hermes;"
echo "         rm $TDIR/daily.conf && systemctl daemon-reload"
