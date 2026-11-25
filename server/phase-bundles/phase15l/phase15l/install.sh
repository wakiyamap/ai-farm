#!/usr/bin/env bash
# Phase 15l (2026-11-21): no false "no baseline in pnl.json" warning after a bot is stopped.
#  farm-dash kept `gate-ctl status` for up to 5 minutes but read pnl.json fresh; `gate stop` removes
#  the bot's baseline at once, so the stopped bot stayed in the live list without a baseline and the
#  page / brief warned "<bot>: no baseline in pnl.json, the live-loss stop cannot judge it".
#  - farm-dash (2 text patches): the status cache is dropped when gate.log changes (every promote,
#    fund, sweep, stop), and a bot without a baseline whose bots/live directory is gone is skipped.
#  gate-ctl, pnl.json, the watchdog and the bots are not touched. farm-dash is restarted.
#  On failure the old farm-dash is restored.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
export PYTHONDONTWRITEBYTECODE=1
F=/opt/farm/bin/farm-dash
REF=cc050e4fe3baf12b160c370581fe463d4194f3bcc266f1bcc5edf12ff9ae4bb7    # after phase 15k (11-21 08:20 JST)
sha() { sha256sum "$1" | cut -d' ' -f1; }
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "== checks (nothing is changed yet)"
for f in patch-15l.py test-15l.py; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$f"
done
echo "  farm-dash sha256 (reference = after 15k / installed)"
echo "    $REF"
echo "    $(sha $F)"
[[ $(sha $F) == "$REF" ]] || echo "  note: farm-dash differs from the reference; the patches decide"
python3 -I -B patch-15l.py apply $F "$tmp"
python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$tmp/farm-dash"
echo "== offline tests (installed farm-dash: report only, 3 of 6 before 15l)"
python3 -I -B test-15l.py $F --old | tail -1
echo "== offline tests (new farm-dash)"
python3 -I -B test-15l.py "$tmp/farm-dash"
U=$(systemctl show -p User --value farm-dash.service); U=${U:-root}
if runuser -u "$U" -- test -x /srv/farm/ws/bots/live; then
  echo "  $U (farm-dash) can see /srv/farm/ws/bots/live"
else
  echo "  note: $U (farm-dash) cannot see /srv/farm/ws/bots/live: part 2 then hides every 'no baseline' line; part 1 still works"
fi

back() {
  echo "!! $1 - restoring farm-dash" >&2
  [[ -f /opt/farm/bin/.farm-dash.bak-15l ]] && cp -a /opt/farm/bin/.farm-dash.bak-15l $F
  systemctl restart farm-dash.service || true
  journalctl -u farm-dash -n 15 --no-pager >&2 || true
  exit 1
}

echo "== install"
[[ -e /opt/farm/bin/.farm-dash.bak-15l ]] || cp -a $F /opt/farm/bin/.farm-dash.bak-15l
install -o "$(stat -c %u $F)" -g "$(stat -c %g $F)" -m "$(stat -c %a $F)" "$tmp/farm-dash" $F
systemctl restart farm-dash.service
ok=0
for _ in $(seq 1 30); do
  if curl -s -m 90 http://127.0.0.1:8090/brief.txt -o "$tmp/brief.txt" && grep -q '^live PnL since promotion' "$tmp/brief.txt"; then ok=1; break; fi
  sleep 2
done
(( ok )) || back "brief.txt has no live PnL line"
systemctl is-active farm-dash.service >/dev/null || back "farm-dash is not active"
echo "  farm-dash active; brief.txt:"
grep -E '^(capital|live PnL since promotion)' "$tmp/brief.txt" | sed 's/^/    /'
if grep -q 'no baseline in pnl.json' "$tmp/brief.txt"; then
  echo "  'no baseline' lines still in the brief (a live bot without a baseline):"
  grep 'no baseline in pnl.json' "$tmp/brief.txt" | sed 's/^/    /'
else
  echo "  no 'no baseline' line in the brief"
fi

echo "== sha256 (expected = patched copy checked above / installed)"
echo "  farm-dash  $(sha "$tmp/farm-dash")"
echo "             $(sha $F)"
echo "Installed phase 15l."
echo "To undo: cp -a /opt/farm/bin/.farm-dash.bak-15l $F && systemctl restart farm-dash"
