#!/usr/bin/env bash
# Phase 12f: farm-relayapi, a local door to the Relay (relay.link) API that keeps the human's API key.
#  - /opt/farm/bin/farm-relayapi (new service, 127.0.0.1:29485, DynamicUser, key from the systemd
#    credential /etc/farm/relayapi.key). Agents call http://127.0.0.1:29485/<path> in place of
#    https://api.relay.link/<path>; the service adds the x-api-key header. Only data endpoints are
#    passed on (quote, price, chains, currencies, requests, intents/status). It cannot send anything.
#  - /etc/farm/relayapi.json (allowed paths, pacing, daily limit; no secrets; kept if it exists)
#  - farm.nft (2 text patches): the earner may reach port 29485; the bots may not
#  - roles/TOOLS.md: one `relayapi` row after the `explorer` row (skipped if that row is not found)
#  - decisions/human/2026-11-16-reaction-time.md and a note for meta
# BEFORE running: put the Relay API key in /etc/farm/relayapi.key (root, mode 600):
#     sudo install -o root -g root -m 600 /dev/stdin /etc/farm/relayapi.key
#     (paste the key, Enter, Ctrl-D). The key is never printed and never leaves the service.
# Checks and offline tests run before anything changes. If Relay rejects the key or the earner
# cannot reach the service, farm.nft and TOOLS.md are restored and the service is stopped.
# run-role, gate, signer, watchdog, relay, explorer and the bots are not touched.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
KEYFILE=/etc/farm/relayapi.key
CONF=/etc/farm/relayapi.json
NFT=/etc/farm/farm.nft
TOOLS=/srv/farm/prompts/roles/TOOLS.md
TBAK=$(dirname $TOOLS)/.TOOLS.md.bak-12f
UNIT=/etc/systemd/system/farm-relayapi.service
PORT=29485
export PYTHONDONTWRITEBYTECODE=1
sha() { sha256sum "$1" | cut -d' ' -f1; }
OLD_NFT=cef17d837175884b7b1f469f4823ec9d0f628a21be0f093e602804099510292d
NEW_NFT=acc2c1df146dbf4a16a9743791641c2b64175e56c7d13cef1b5a2d74d3e15310
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "== checks (nothing is changed yet)"
if [[ ! -s $KEYFILE ]]; then
  echo "  $KEYFILE is missing or empty. Create it first (the key is not echoed anywhere):" >&2
  echo "    sudo install -o root -g root -m 600 /dev/stdin $KEYFILE    # paste the key, Enter, Ctrl-D" >&2
  exit 1
fi
[[ $(stat -c '%U:%G %a' $KEYFILE) == "root:root 600" ]] || { chown root:root $KEYFILE; chmod 600 $KEYFILE; echo "  $KEYFILE: set to root:root 600"; }
python3 -I -B - $KEYFILE <<'PY' || { echo "  $KEYFILE does not look like one API key (one line, no spaces, 8 to 200 characters). Nothing was changed." >&2; exit 1; }
import re, sys
k = open(sys.argv[1], encoding="utf-8").read().strip()
sys.exit(0 if re.fullmatch(r"[\x21-\x7e]{8,200}", k) else 1)
PY
echo "  $KEYFILE: present, root 600, one key of $(tr -d '\n\r ' < $KEYFILE | wc -c) characters"
for f in patch-12f.py test-12f.py farm-relayapi; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$f"
done
python3 -I -B -c 'import json,sys; json.load(open(sys.argv[1]))' relayapi.json
hn=$(sha $NFT)
if [[ $hn == "$NEW_NFT" ]]; then
  echo "  farm.nft is already the 12f version"
  cp $NFT "$tmp/"
elif [[ $hn == "$OLD_NFT" ]]; then
  echo "  farm.nft: as expected"
  python3 -I -B patch-12f.py check $NFT
  python3 -I -B patch-12f.py apply $NFT "$tmp"
  [[ $(sha "$tmp/farm.nft") == "$NEW_NFT" ]] || { echo "  the patched farm.nft does not have the expected sha256; nothing was changed" >&2; exit 1; }
else
  echo "  farm.nft changed since the bundle was built. Nothing was changed." >&2
  echo "    expected $OLD_NFT" >&2
  echo "    got      $hn" >&2
  exit 1
fi
nft -c -f "$tmp/farm.nft"
echo "  farm.nft: syntax ok"
if ! systemctl is-active --quiet farm-relayapi.service && ss -ltnH "sport = :$PORT" | grep -q .; then
  echo "  port $PORT is already in use by something else. Nothing was changed." >&2; exit 1
fi
echo "== offline tests"
python3 -I -B test-12f.py farm-relayapi "$tmp/farm.nft"

undo() {
  echo "!! $1 - restoring farm.nft and TOOLS.md, stopping farm-relayapi" >&2
  if [[ -f $NFT.bak-12f ]]; then cat "$NFT.bak-12f" > "$NFT"; nft -f "$NFT" || true; fi
  [[ -f $TBAK ]] && cp -a "$TBAK" $TOOLS
  systemctl disable --now farm-relayapi.service 2>/dev/null || true
  journalctl -u farm-relayapi -n 15 --no-pager >&2 || true
  exit 1
}
code() { curl -s -m 40 -o "$tmp/body" -w '%{http_code}' "$@" || true; }

echo "== service"
[[ -e $CONF ]] || install -o root -g root -m 644 relayapi.json $CONF
install -o root -g root -m 755 farm-relayapi $B/
install -o root -g root -m 644 units/farm-relayapi.service $UNIT
systemctl daemon-reload
systemctl enable farm-relayapi.service >/dev/null 2>&1 || true
systemctl restart farm-relayapi.service
ok=0
for _ in $(seq 1 20); do
  if curl -s -m 3 "http://127.0.0.1:$PORT/health" | grep -q '"ok": *true'; then ok=1; break; fi
  sleep 1
done
(( ok )) || undo "farm-relayapi does not answer on 127.0.0.1:$PORT"
systemctl is-active farm-relayapi.service

echo "== real calls through the service"
c=$(code "http://127.0.0.1:$PORT/chains")
echo "  GET /chains: HTTP $c ($(stat -c %s "$tmp/body") bytes)"
[[ $c == 200 ]] || undo "Relay did not answer /chains with 200 through the service"
c=$(code "http://127.0.0.1:$PORT/requests/v3?limit=1")
echo "  GET /requests/v3?limit=1 (the call that needed a key): HTTP $c ($(stat -c %s "$tmp/body") bytes)"
case $c in
  200) echo "  the key is accepted" ;;
  401|403) head -c 300 "$tmp/body" >&2; echo >&2; undo "Relay rejected the API key (HTTP $c)" ;;
  *) echo "  !! not 200 and not a key refusal; the service stays installed. First bytes of the answer:"
     head -c 300 "$tmp/body" | sed 's/^/     /'; echo ;;
esac
c=$(code -X POST -H 'Content-Type: application/json' -d '{}' "http://127.0.0.1:$PORT/execute/swap")
echo "  POST /execute/swap: HTTP $c (expected 403: refused here, never sent to Relay)"
[[ $c == 403 ]] || undo "a path outside the allow list was not refused"
if journalctl -u farm-relayapi --no-pager -n 200 2>/dev/null \
     | python3 -I -c 'import sys; k = open(sys.argv[1]).read().strip(); sys.exit(0 if k and k in sys.stdin.read() else 1)' $KEYFILE; then
  undo "the API key appears in the service's journal"
fi
echo "  the key does not appear in the service's journal"

echo "== farm.nft (earner may reach $PORT)"
if [[ $hn != "$NEW_NFT" ]]; then
  [[ -e $NFT.bak-12f ]] || cp -a "$NFT" "$NFT.bak-12f"
  cat "$tmp/farm.nft" > "$NFT"
  nft -f "$NFT" || undo "nft refused the new rules"
fi
runuser -u earner -- env PATH=/usr/bin:/bin curl -s -m 5 -o /dev/null "http://127.0.0.1:$PORT/health" || undo "the earner cannot reach farm-relayapi"
echo "  earner: reaches farm-relayapi"
if runuser -u farmbot -- python3 -I -c "import socket; socket.create_connection(('127.0.0.1', $PORT), 3)" 2>/dev/null; then
  echo "  !! farmbot can reach port $PORT (expected: refused). Check the rules." >&2
else
  echo "  farmbot: refused, as intended"
fi
echo "  sha256 (expected / installed)"
echo "    farm.nft $NEW_NFT"
echo "             $(sha $NFT)"

echo "== TOOLS.md"
runuser -u harness -- cat $TOOLS > "$tmp/TOOLS.in"
python3 -I -B patch-12f.py tools "$tmp/TOOLS.in" "$tmp/TOOLS.md"
if ! cmp -s "$tmp/TOOLS.in" "$tmp/TOOLS.md"; then
  [[ -e $TBAK ]] || cp -a $TOOLS "$TBAK"
  install -o harness -g harness -m 644 "$tmp/TOOLS.md" $TOOLS
fi
echo "== assembled prompts (limit 60000, keep at or under 56000)"
for i in $(awk '!/^#/ && NF {print $1}' /etc/farm/roles.conf); do
  if ! /opt/farm/bin/assemble-prompt "$i"; then
    [[ -f $TBAK ]] && cp -a "$TBAK" $TOOLS
    echo "  assemble-prompt failed for $i; TOOLS.md restored (everything else stays installed)" >&2; exit 1
  fi
  n=$(stat -c %s "/srv/farm/runners/$i/prompt.md")
  echo "  $i: $n bytes"
  if (( n > 56000 )) && [[ -f $TBAK ]]; then
    cp -a "$TBAK" $TOOLS
    for j in $(awk '!/^#/ && NF {print $1}' /etc/farm/roles.conf); do /opt/farm/bin/assemble-prompt "$j" || true; done
    echo "  $i would be over 56000 bytes: TOOLS.md restored; meta adds a shorter row from the note" >&2
    break
  fi
done

echo "== decision and note for meta"
install -o root -g root -m 644 decisions-2026-11-16-reaction-time.md /srv/farm/ws/decisions/human/2026-11-16-reaction-time.md
install -o root -g root -m 644 inbox-meta-2026-11-16-phase12f-relayapi.md /srv/farm/ws/inbox/meta/2026-11-16-phase12f-relayapi.md
echo "Installed phase 12f."
echo "Paste everything from '== checks' down (the key is not in this output)."
echo "To undo: restore $NFT.bak-12f (then: nft -f $NFT) and $TBAK,"
echo "         systemctl disable --now farm-relayapi, remove $UNIT, $B/farm-relayapi, $CONF, $KEYFILE"
