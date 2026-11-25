#!/usr/bin/env bash
# Phase 15j (2026-11-20): the dashboard and brief show the live bots' profit.
#  "realized today" was the gate's realized_usd, written only when a stopped bot is swept, so the
#  profit sitting in live bots' wallets (peapods-arb-arbitrum +1.64 USD) showed nowhere.
#  - farm-dash (text patches): live PnL since promotion per bot and in total (gains / losses), live
#    PnL today (UTC) from a 00:00 UTC snapshot (one gate status a day; kept in
#    /var/lib/farmgate/dash-pnl-day.json with 14 days of daily totals), swept PnL all time from
#    gate.log. "realized today" becomes "swept today". The gate, pnl.json and the daily-loss guard are
#    not touched.
#  farm-dash is restarted (the page is down for a second). On failure the old farm-dash is restored.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
export PYTHONDONTWRITEBYTECODE=1
F=/opt/farm/bin/farm-dash
REF=bffd08e9fff10f85524bad2a23c62de1b1c774e791ce5457b49ad573eb1585cc    # sent 2026-11-20 08:22 JST
sha() { sha256sum "$1" | cut -d' ' -f1; }
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "== checks (nothing is changed yet)"
for f in patch-15j.py test-15j.py; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$f"
done
echo "  farm-dash sha256 (reference = sent 11-20 08:22 / installed)"
echo "    $REF"
echo "    $(sha $F)"
[[ $(sha $F) == "$REF" ]] || echo "  note: farm-dash differs from the reference; the patches decide"
python3 -I -B patch-15j.py apply $F "$tmp"
python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$tmp/farm-dash"
echo "== offline tests (installed farm-dash: report only, 0 of 9 before 15j)"
python3 -I -B test-15j.py $F --old | tail -1
echo "== offline tests (new farm-dash)"
python3 -I -B test-15j.py "$tmp/farm-dash"
runuser -u farmgate -- test -w /var/lib/farmgate || { echo "farmgate cannot write /var/lib/farmgate" >&2; exit 1; }

back() {
  echo "!! $1 - restoring farm-dash" >&2
  [[ -f /opt/farm/bin/.farm-dash.bak-15j ]] && cp -a /opt/farm/bin/.farm-dash.bak-15j $F
  systemctl restart farm-dash.service || true
  journalctl -u farm-dash -n 15 --no-pager >&2 || true
  exit 1
}

echo "== install"
[[ -e /opt/farm/bin/.farm-dash.bak-15j ]] || cp -a $F /opt/farm/bin/.farm-dash.bak-15j
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
grep -E '^(live PnL since promotion|  in profit:|swept today)' "$tmp/brief.txt" | sed 's/^/    /'
if [[ -f /var/lib/farmgate/dash-pnl-day.json ]]; then
  echo "  day snapshot: $(python3 -I -c 'import json; d=json.load(open("/var/lib/farmgate/dash-pnl-day.json")); print(d["day"], "since", d["since"], "-", len(d["start"]), "bots")')"
fi

echo "== sha256 (expected = patched copy checked above / installed)"
echo "  farm-dash  $(sha "$tmp/farm-dash")"
echo "             $(sha $F)"
echo "Installed phase 15j. 'live PnL today' counts from this first snapshot until 00:00 UTC, then from each 00:00 UTC."
echo "To undo: cp -a /opt/farm/bin/.farm-dash.bak-15j $F && systemctl restart farm-dash"
