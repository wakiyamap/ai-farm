#!/usr/bin/env bash
# Phase 11a (2026-11-13): farm-feed - bots wait for a block or an event instead of polling.
#   /opt/farm/bin/farm-feed       WebSocket subscriptions at Alchemy (standard library only), served as
#                                 HTTP long-polls on 127.0.0.1:8546 (/head/<chain>, /logs/<chain>, /health)
#   farm-feed.service             user farmrelay (same Alchemy key as rpc-relay), enabled
#   /etc/farm/feed.json           limits (kept if it exists): /head on ethereum only, 700,000 CU/day in
#                                 total, 150,000 CU/day per log filter, idle subscriptions dropped at 180 s
#   /etc/farm/farm.nft            earner and farmbot may reach 8546
#   /srv/farm/prompts/common.md   Principle 2: same block = latency race (out of scope); one block later
#                                 may be tried through the feed but is not counted; two or more count
#   inbox/meta note               reference for wiki infra/feed.md
# Order: everything that needs no change first (patch texts, nft syntax, 12 offline tests, the port,
# one real head through the new client as farmrelay - about 55 CU). Then the service; if it does not
# answer, it is removed again and nothing else is touched. Then nft (restored if the reload fails),
# then common.md (restored if a prompt no longer fits).
# rpc-relay, farm-signer, farm-watchdog and the bots are neither changed nor restarted.
# The decision text is NOT installed by this script (the human places it).
# Backups: /etc/farm/.farm.nft.bak-11a, /srv/farm/prompts/.common.md.bak-11a. Safe to re-run.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin E=/etc/farm S=/etc/systemd/system
C=/srv/farm/prompts/common.md
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
export PYTHONDONTWRITEBYTECODE=1
pyc() { python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$1"; }
get() { python3 -I -B -c 'import sys, urllib.request; print(urllib.request.urlopen(sys.argv[1], timeout=float(sys.argv[2])).read().decode())' "$1" "$2"; }

for f in farm-feed patch-11a.py test-11a.py; do pyc "$f"; done
python3 -I -B -c 'import json; json.load(open("feed.json"))'
echo "== patch texts"
python3 -I -B patch-11a.py check "$E/farm.nft" "$C"
python3 -I -B patch-11a.py apply "$E/farm.nft" "$C" "$tmp" >/dev/null
nft -c -f "$tmp/farm.nft"
echo "  common.md: $(stat -c %s "$C") -> $(stat -c %s "$tmp/common.md") bytes"
echo "== offline tests"
python3 -I -B test-11a.py farm-feed
echo "== port 8546"
if systemctl is-active --quiet farm-feed; then
  echo "  farm-feed is already running (re-run): it will be restarted with this version"
elif ss -ltnH 'sport = :8546' | grep -q .; then
  ss -ltnpH 'sport = :8546' >&2
  echo "port 8546 is in use by something else; nothing was changed" >&2
  exit 1
else
  echo "  free"
fi
echo "== one real head through the new client, as farmrelay (before any change)"
install -o root -g root -m 755 farm-feed "$tmp/farm-feed"
chmod 755 "$tmp"
runuser -u farmrelay -- python3 -I -B "$tmp/farm-feed" --check ethereum || {
  echo "the check failed; nothing was changed. (key: $E/alchemy.key readable by farmrelay? WebSockets enabled for the Alchemy app?)" >&2
  exit 1
}

echo "== install farm-feed and start it"
install -o root -g root -m 755 farm-feed "$B/farm-feed"
[[ -e "$E/feed.json" ]] && echo "  $E/feed.json kept" || install -o root -g root -m 644 feed.json "$E/feed.json"
install -o root -g root -m 644 units/farm-feed.service "$S/farm-feed.service"
systemctl daemon-reload
systemctl enable farm-feed 2>&1 | grep -v '^Created symlink' || true
systemctl restart farm-feed
ok=0
for _ in $(seq 1 20); do
  if get http://127.0.0.1:8546/health 3 >"$tmp/health" 2>/dev/null; then ok=1; break; fi
  sleep 1
done
if [[ $ok != 1 ]]; then
  echo "!! farm-feed does not answer - removing the service again (nothing else was changed)" >&2
  journalctl -u farm-feed -n 20 --no-pager >&2 || true
  systemctl disable --now farm-feed || true
  rm -f "$S/farm-feed.service"
  systemctl daemon-reload
  exit 1
fi
python3 -I -B - "$tmp/health" <<'PY'
import json, sys
h = json.load(open(sys.argv[1]))
print(f"  health ok: chains {', '.join(sorted(h['chains']))}; /head on {h['heads_offered_on']}; "
      f"budget {h['daily_cu_budget']} CU/day; used today {h['cu_today']}")
PY

echo "== nft: earner and farmbot may reach 8546"
[[ -e "$E/.farm.nft.bak-11a" ]] || cp -a "$E/farm.nft" "$E/.farm.nft.bak-11a"
cp -a "$E/farm.nft" "$tmp/farm.nft.before"
install -o "$(stat -c %u "$E/farm.nft")" -g "$(stat -c %g "$E/farm.nft")" -m "$(stat -c %a "$E/farm.nft")" "$tmp/farm.nft" "$E/farm.nft"
if ! systemctl restart farm-nft; then
  echo "!! farm-nft did not reload - restoring farm.nft" >&2
  cp -a "$tmp/farm.nft.before" "$E/farm.nft"
  systemctl restart farm-nft || true
  exit 1
fi
nft list table inet farm | grep -c '8546' | sed 's/^/  nft rules with 8546: /' || true
for u in farmbot earner; do
  if runuser -u "$u" -- python3 -I -B -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8546/health", timeout=5).read()' 2>/dev/null; then
    echo "  $u reaches the feed"
  else
    echo "  !! $u cannot reach http://127.0.0.1:8546/health (check: nft list table inet farm)"
  fi
done

echo "== a head through the service (the subscription is released 180 s after this call)"
get 'http://127.0.0.1:8546/head/ethereum?timeout=40' 50 | sed 's/^/  /' || echo "  !! no head: journalctl -u farm-feed -n 20"
get http://127.0.0.1:8546/health 5 | python3 -I -B -c 'import json,sys; h=json.load(sys.stdin); e=h["chains"]["ethereum"]; print("  ethereum:", e["status"], "cu_today", e["cu_today"])' || true

echo "== common.md"
assemble_all() {
  local bad=0 inst
  while read -r inst _; do
    [[ -z "$inst" || "$inst" == \#* ]] && continue
    if "$B/assemble-prompt" "$inst"; then
      echo "  $inst: $(stat -c %s "/srv/farm/runners/$inst/prompt.md") bytes"
    else
      echo "  $inst: FAILED (see the line above)"
      bad=1
    fi
  done < "$E/roles.conf"
  return $bad
}
[[ -e /srv/farm/prompts/.common.md.bak-11a ]] || cp -a "$C" /srv/farm/prompts/.common.md.bak-11a
cp -a "$C" "$tmp/common.md.before"
install -o "$(stat -c %u "$C")" -g "$(stat -c %g "$C")" -m "$(stat -c %a "$C")" "$tmp/common.md" "$C"
if ! assemble_all; then
  echo "!! an instance no longer fits - restoring common.md and assembling again (the feed stays installed)" >&2
  cp -a "$tmp/common.md.before" "$C"
  assemble_all || true
  exit 1
fi

note=/srv/farm/ws/inbox/meta/2026-11-13-phase11a-feed.md
[[ -e $note ]] || install -m 664 inbox-meta-2026-11-13-phase11a-feed.md "$note"
echo "Installed phase 11a. Paste everything from '== patch texts' down."
echo "Next: place the decision (decisions-2026-11-13-next-block-feed.md) in decisions/human/ if you agree with its text."
