#!/usr/bin/env bash
# Phase 16c (2026-11-23): farm-dash shows grad bots apart from trial bots, and the graduation candidates.
#  decisions/human/2026-11-24-graduate-and-builder-focus.md: candidates = trial bots (not ethereum)
#  live >= 72 h, PnL since promotion >= +1 USD (gate status) and >= 3 `send_result: won` since
#  promotion; grads are grad-<target>-<chain>, at most 5 live.
#  - farm-dash (6 text patches + block-16c.py): "Live bots" becomes Grad bots / Live bots: trial and
#    one-shot / Graduation candidates (+ one condition short); a "Grad bots" tile; grad and candidate
#    lines in brief.txt after "in profit"; a warning above 5 live grads; "graduation" in /data.json.
#  - won / sends: files under bots/live/<id>/logs/ (lines with a time before the promotion are not
#    counted); when they hold no send_result line, the bot@<id> journal (at most 4 calls per refresh).
#  - promote time: the newest `promote` record of the bot in gate.log.
#  gate-ctl, pnl.json, the watchdog and the bots are not touched. farm-dash is restarted.
#  On failure the old farm-dash is restored.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
export PYTHONDONTWRITEBYTECODE=1
F=/opt/farm/bin/farm-dash
REF=ae04cc68f4fd22853f43d7885e630131d6f619d9c385cf56e1f48049db046c42    # the copy sent 11-23 (after 15l)
NEW=c995b3513680bd056198ea2d609ddc12e6f83cb71ec133f6ad7279818c1234c9    # REF + 16c
sha() { sha256sum "$1" | cut -d' ' -f1; }
tmp=$(mktemp -d)
chmod 755 "$tmp"
trap 'rm -rf "$tmp"' EXIT

echo "== checks (nothing is changed yet)"
for f in patch-16c.py test-16c.py block-16c.py; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$f"
done
echo "  farm-dash sha256 (reference = sent 11-23 / installed)"
echo "    $REF"
echo "    $(sha $F)"
[[ $(sha $F) == "$REF" ]] || echo "  note: farm-dash differs from the reference; the patches decide"
python3 -I -B patch-16c.py apply $F "$tmp"
python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$tmp/farm-dash"
[[ $(sha $F) != "$REF" || $(sha "$tmp/farm-dash") == "$NEW" ]] || { echo "patched copy is not the expected $NEW" >&2; exit 1; }
echo "== offline tests (installed farm-dash: report only, 0 of 9 before 16c)"
python3 -I -B test-16c.py $F --old | tail -1
echo "== offline tests (new farm-dash)"
python3 -I -B test-16c.py "$tmp/farm-dash"
U=$(systemctl show -p User --value farm-dash.service); U=${U:-root}
echo "== probe as $U (farm-dash's user), read-only: promote time, won / sends and their source"
cp test-16c.py "$tmp/"; chmod 644 "$tmp/test-16c.py" "$tmp/farm-dash"
runuser -u "$U" -- python3 -I -B "$tmp/test-16c.py" "$tmp/farm-dash" --probe || echo "  note: the probe failed; the page shows what it can read"

back() {
  echo "!! $1 - restoring farm-dash" >&2
  [[ -f /opt/farm/bin/.farm-dash.bak-16c ]] && cp -a /opt/farm/bin/.farm-dash.bak-16c $F
  systemctl restart farm-dash.service || true
  journalctl -u farm-dash -n 15 --no-pager >&2 || true
  exit 1
}

echo "== install"
[[ -e /opt/farm/bin/.farm-dash.bak-16c ]] || cp -a $F /opt/farm/bin/.farm-dash.bak-16c
install -o "$(stat -c %u $F)" -g "$(stat -c %g $F)" -m "$(stat -c %a $F)" "$tmp/farm-dash" $F
systemctl restart farm-dash.service
ok=0
for _ in $(seq 1 30); do
  if curl -s -m 90 http://127.0.0.1:8090/brief.txt -o "$tmp/brief.txt" && grep -q '^graduation candidates' "$tmp/brief.txt"; then ok=1; break; fi
  sleep 2
done
(( ok )) || back "brief.txt has no graduation candidates line"
curl -s -m 90 http://127.0.0.1:8090/ -o "$tmp/page.html" || back "the page does not answer"
grep -q '<h2>Grad bots (' "$tmp/page.html" && grep -q '<h2>Graduation candidates (' "$tmp/page.html" || back "the page has no grad sections"
systemctl is-active farm-dash.service >/dev/null || back "farm-dash is not active"
echo "  farm-dash active; brief.txt:"
grep -E '^(live PnL since promotion|grad bots live|  grad |graduation candidates|  - |  one condition short|  note: no send_result)' "$tmp/brief.txt" | sed 's/^/    /'

echo "== sha256 (expected = patched copy checked above / installed)"
echo "  farm-dash  $(sha "$tmp/farm-dash")"
echo "             $(sha $F)"
echo "Installed phase 16c."
echo "To undo: cp -a /opt/farm/bin/.farm-dash.bak-16c $F && systemctl restart farm-dash"
