#!/usr/bin/env bash
# Phase 12e: (1) farm-explorer, a local read-only door to the Etherscan V2 API that keeps the API
# key, with the `explorer` command for agents; (2) WebFetch for researcher-claude.
#  - /opt/farm/bin/farm-explorer (new service, 127.0.0.1:29484, DynamicUser, key from the systemd
#    credential /etc/farm/explorer.key) and /opt/farm/bin/explorer (CLI). Six fixed read operations
#    on a known address (source, abi, creation, txs, internal, tokentx); nothing else is passed on.
#    No search by name: Etherscan's API has none.
#  - /etc/farm/explorer.json (chains, pacing, daily limit; no secrets; kept if it exists)
#  - run-role (2 text patches): `Bash(explorer *)` for every claude role, `WebFetch` for the
#    researcher role only
#  - farm.nft (2 text patches): the earner may reach port 29484; the bots may not
#  - roles/TOOLS.md: one `explorer` row after the `web` row (skipped if the row is not found)
#  - a note for meta
# BEFORE running: put the Etherscan API key in /etc/farm/explorer.key (root, mode 600):
#     sudo install -o root -g root -m 600 /dev/stdin /etc/farm/explorer.key
#     (paste the key, Enter, Ctrl-D). The key is never printed and never leaves the service.
# Checks and offline tests run before anything changes. If the key is rejected, no chain answers,
# or the earner cannot reach the service, run-role, farm.nft and TOOLS.md are restored and the
# service is stopped. gate, signer, watchdog, relay and the bots are not touched.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
KEYFILE=/etc/farm/explorer.key
CONF=/etc/farm/explorer.json
NFT=/etc/farm/farm.nft
TOOLS=/srv/farm/prompts/roles/TOOLS.md
UNIT=/etc/systemd/system/farm-explorer.service
PORT=29484
export PYTHONDONTWRITEBYTECODE=1
sha() { sha256sum "$1" | cut -d' ' -f1; }
OLD_RUN=a62cee621f89f1f01936a5830c3d4bee6d987c7ce7c6fa8982b63b7be8e4782a
NEW_RUN=594c299e5ae8573281e7135bfc4f91321da5b4d9808c65226ccda0b610bbd1c9
OLD_NFT=d524696113cdb43f6011c5c07af87294f4f2d694c2ffac14ea6714dae83bf9c7
NEW_NFT=cef17d837175884b7b1f469f4823ec9d0f628a21be0f093e602804099510292d
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "== checks (nothing is changed yet)"
if [[ ! -s $KEYFILE ]]; then
  echo "  $KEYFILE is missing or empty. Create it first (the key is not echoed anywhere):" >&2
  echo "    sudo install -o root -g root -m 600 /dev/stdin $KEYFILE    # paste the key, Enter, Ctrl-D" >&2
  exit 1
fi
[[ $(stat -c '%U:%G %a' $KEYFILE) == "root:root 600" ]] || { chown root:root $KEYFILE; chmod 600 $KEYFILE; echo "  $KEYFILE: set to root:root 600"; }
python3 -I -B - $KEYFILE <<'PY' || { echo "  $KEYFILE does not look like one API key (one line of letters and digits). Nothing was changed." >&2; exit 1; }
import re, sys
k = open(sys.argv[1], encoding="utf-8").read().strip()
sys.exit(0 if re.fullmatch(r"[A-Za-z0-9]{16,80}", k) else 1)
PY
echo "  $KEYFILE: present, root 600, one key of $(tr -d '\n\r ' < $KEYFILE | wc -c) characters"
for f in patch-12e.py test-12e.py farm-explorer explorer; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$f"
done
python3 -I -B -c 'import json,sys; json.load(open(sys.argv[1]))' explorer.json
hr=$(sha $B/run-role); hn=$(sha $NFT)
if [[ $hr == "$NEW_RUN" && $hn == "$NEW_NFT" ]]; then
  echo "  run-role and farm.nft are already the 12e versions"
  cp $B/run-role $NFT "$tmp/"
elif [[ $hr == "$OLD_RUN" && $hn == "$OLD_NFT" ]]; then
  echo "  run-role and farm.nft: as expected"
  python3 -I -B patch-12e.py check $B/run-role $NFT
  python3 -I -B patch-12e.py apply $B/run-role $NFT "$tmp"
  if [[ $(sha "$tmp/run-role") != "$NEW_RUN" || $(sha "$tmp/farm.nft") != "$NEW_NFT" ]]; then
    echo "  patched files do not have the expected sha256; nothing was changed" >&2; exit 1
  fi
else
  echo "  run-role or farm.nft changed since the bundle was built. Nothing was changed." >&2
  echo "    run-role expected $OLD_RUN" >&2
  echo "             got      $hr" >&2
  echo "    farm.nft expected $OLD_NFT" >&2
  echo "             got      $hn" >&2
  exit 1
fi
bash -n "$tmp/run-role"
nft -c -f "$tmp/farm.nft"
echo "  farm.nft: syntax ok"
if ! systemctl is-active --quiet farm-explorer.service && ss -ltnH "sport = :$PORT" | grep -q .; then
  echo "  port $PORT is already in use by something else. Nothing was changed." >&2; exit 1
fi
echo "== offline tests"
python3 -I -B test-12e.py farm-explorer explorer "$tmp/run-role" "$tmp/farm.nft"

undo() {
  echo "!! $1 - restoring run-role, farm.nft and TOOLS.md, stopping farm-explorer" >&2
  [[ -f $B/.run-role.bak-12e ]] && cp -a $B/.run-role.bak-12e $B/run-role
  if [[ -f $NFT.bak-12e ]]; then cat "$NFT.bak-12e" > "$NFT"; nft -f "$NFT" || true; fi
  [[ -f $(dirname $TOOLS)/.TOOLS.md.bak-12e ]] && cp -a "$(dirname $TOOLS)/.TOOLS.md.bak-12e" $TOOLS
  systemctl disable --now farm-explorer.service 2>/dev/null || true
  journalctl -u farm-explorer -n 15 --no-pager >&2 || true
  exit 1
}

echo "== service"
[[ -e $CONF ]] || install -o root -g root -m 644 explorer.json $CONF
install -o root -g root -m 755 farm-explorer explorer $B/
install -o root -g root -m 644 units/farm-explorer.service $UNIT
systemctl daemon-reload
systemctl enable farm-explorer.service >/dev/null 2>&1 || true
systemctl restart farm-explorer.service
ok=0
for _ in $(seq 1 20); do
  if curl -s -m 3 "http://127.0.0.1:$PORT/health" | grep -q '"ok": *true'; then ok=1; break; fi
  sleep 1
done
(( ok )) || undo "farm-explorer does not answer on 127.0.0.1:$PORT"
systemctl is-active farm-explorer.service

echo "== which chains this key covers (one call per chain)"
runuser -u harness -- $B/explorer chains | tee "$tmp/chains.out" | sed 's/^/  /'
grep -q 'invalid_key' "$tmp/chains.out" && undo "Etherscan rejected the API key"
grep -q ': ok ' "$tmp/chains.out" || undo "no chain answered with this key"
echo "== one real lookup (USDC on ethereum: expect name FiatTokenProxy, a proxy with an implementation)"
runuser -u harness -- $B/explorer source ethereum 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 | head -n 6 | sed 's/^/  /' \
  || echo "  (lookup failed; the service stays installed - see the message above)"
if journalctl -u farm-explorer --no-pager -n 200 2>/dev/null \
     | python3 -I -c 'import sys; k = open(sys.argv[1]).read().strip(); sys.exit(0 if k and k in sys.stdin.read() else 1)' $KEYFILE; then
  undo "the API key appears in the service's journal"
fi
echo "  the key does not appear in the service's journal"

echo "== farm.nft (earner may reach $PORT)"
if [[ $hn != "$NEW_NFT" ]]; then
  [[ -e $NFT.bak-12e ]] || cp -a "$NFT" "$NFT.bak-12e"
  cat "$tmp/farm.nft" > "$NFT"
  nft -f "$NFT" || undo "nft refused the new rules"
fi
runuser -u earner -- env PATH=/usr/bin:/bin $B/explorer chains > /dev/null || undo "the earner cannot reach farm-explorer"
echo "  earner: reaches farm-explorer"
if runuser -u farmbot -- python3 -I -c "import socket; socket.create_connection(('127.0.0.1', $PORT), 3)" 2>/dev/null; then
  echo "  !! farmbot can reach port $PORT (expected: refused). Check the rules." >&2
else
  echo "  farmbot: refused, as intended"
fi

echo "== run-role"
if [[ $hr != "$NEW_RUN" ]]; then
  [[ -e $B/.run-role.bak-12e ]] || cp -a $B/run-role $B/.run-role.bak-12e
  install -o root -g root -m 755 "$tmp/run-role" $B/run-role
fi
echo "  sha256 (expected / installed)"
echo "    run-role $NEW_RUN"
echo "             $(sha $B/run-role)"
echo "    farm.nft $NEW_NFT"
echo "             $(sha $NFT)"

echo "== TOOLS.md"
runuser -u harness -- cat $TOOLS > "$tmp/TOOLS.in"
python3 -I -B patch-12e.py tools "$tmp/TOOLS.in" "$tmp/TOOLS.md"
if ! cmp -s "$tmp/TOOLS.in" "$tmp/TOOLS.md"; then
  [[ -e $(dirname $TOOLS)/.TOOLS.md.bak-12e ]] || cp -a $TOOLS "$(dirname $TOOLS)/.TOOLS.md.bak-12e"
  install -o harness -g harness -m 644 "$tmp/TOOLS.md" $TOOLS
fi
echo "== assembled prompts (limit 60000, keep at or under 56000)"
for i in $(awk '!/^#/ && NF {print $1}' /etc/farm/roles.conf); do
  if ! /opt/farm/bin/assemble-prompt "$i"; then
    [[ -f $(dirname $TOOLS)/.TOOLS.md.bak-12e ]] && cp -a "$(dirname $TOOLS)/.TOOLS.md.bak-12e" $TOOLS
    echo "  assemble-prompt failed for $i; TOOLS.md restored (everything else stays installed)" >&2; exit 1
  fi
  n=$(stat -c %s "/srv/farm/runners/$i/prompt.md")
  echo "  $i: $n bytes"
  if (( n > 56000 )); then
    cp -a "$(dirname $TOOLS)/.TOOLS.md.bak-12e" $TOOLS
    /opt/farm/bin/assemble-prompt "$i" || true
    echo "  $i would be over 56000 bytes: TOOLS.md restored; meta adds a shorter row from the note" >&2
    break
  fi
done

echo "== note for meta"
install -o root -g root -m 644 inbox-meta-2026-11-15-phase12e-explorer-webfetch.md \
  /srv/farm/ws/inbox/meta/2026-11-15-phase12e-explorer-webfetch.md
echo "Installed phase 12e. Sessions that are running keep their old tool list until their next start."
echo "Paste everything from '== checks' down (the key is not in this output)."
echo "To undo: restore $B/.run-role.bak-12e, $NFT.bak-12e (then: nft -f $NFT) and the TOOLS.md backup,"
echo "         systemctl disable --now farm-explorer, remove $UNIT, $B/farm-explorer, $B/explorer, $CONF, $KEYFILE"
