#!/usr/bin/env bash
# Phase 16d (2026-11-23): farm-dash counts sends in the format the live bots write.
#  The bots log {"ev": "send_result", "result": "won" | "lost" | "unknown", ...}; 16c looked for
#  `send_result: won` and found 0 for every bot. One text patch of _count_lines() (16c must be in).
#  The probe (as farm-dash's user, read-only) then prints won / sends per live bot.
#  gate-ctl, pnl.json, the watchdog and the bots are not touched. farm-dash is restarted.
#  On failure the old farm-dash is restored.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
export PYTHONDONTWRITEBYTECODE=1
F=/opt/farm/bin/farm-dash
REF=c995b3513680bd056198ea2d609ddc12e6f83cb71ec133f6ad7279818c1234c9    # after phase 16c (11-23 15:36 JST)
NEW=5b2e98961c8e3c4362df009cadf924068e81002f64c16be9a297ad4f4a0a0a12    # REF + 16d
sha() { sha256sum "$1" | cut -d' ' -f1; }
tmp=$(mktemp -d)
chmod 755 "$tmp"
trap 'rm -rf "$tmp"' EXIT

echo "== checks (nothing is changed yet)"
for f in patch-16d.py test-16d.py test-16c.py; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$f"
done
echo "  farm-dash sha256 (reference = after 16c / installed)"
echo "    $REF"
echo "    $(sha $F)"
[[ $(sha $F) == "$REF" ]] || echo "  note: farm-dash differs from the reference; the patch decides"
python3 -I -B patch-16d.py apply $F "$tmp"
python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$tmp/farm-dash"
[[ $(sha $F) != "$REF" || $(sha "$tmp/farm-dash") == "$NEW" ]] || { echo "patched copy is not the expected $NEW" >&2; exit 1; }
echo "== offline tests (installed farm-dash: report only, 1 of 3 before 16d)"
python3 -I -B test-16d.py $F --old | tail -1
echo "== offline tests (new farm-dash)"
python3 -I -B test-16d.py "$tmp/farm-dash"
python3 -I -B test-16c.py "$tmp/farm-dash" | tail -1
U=$(systemctl show -p User --value farm-dash.service); U=${U:-root}
echo "== probe as $U, read-only: won / sends per live bot since its promotion"
cp test-16c.py "$tmp/"; chmod 644 "$tmp/test-16c.py" "$tmp/farm-dash"
runuser -u "$U" -- python3 -I -B "$tmp/test-16c.py" "$tmp/farm-dash" --probe | sed -E 's/ · logs \(1 file\(s\)\).*$//' \
  || echo "  note: the probe failed; the page shows what it can read"

back() {
  echo "!! $1 - restoring farm-dash" >&2
  [[ -f /opt/farm/bin/.farm-dash.bak-16d ]] && cp -a /opt/farm/bin/.farm-dash.bak-16d $F
  systemctl restart farm-dash.service || true
  journalctl -u farm-dash -n 15 --no-pager >&2 || true
  exit 1
}

echo "== install"
[[ -e /opt/farm/bin/.farm-dash.bak-16d ]] || cp -a $F /opt/farm/bin/.farm-dash.bak-16d
install -o "$(stat -c %u $F)" -g "$(stat -c %g $F)" -m "$(stat -c %a $F)" "$tmp/farm-dash" $F
systemctl restart farm-dash.service
ok=0
for _ in $(seq 1 30); do
  if curl -s -m 90 http://127.0.0.1:8090/brief.txt -o "$tmp/brief.txt" && grep -q '^graduation candidates' "$tmp/brief.txt"; then ok=1; break; fi
  sleep 2
done
(( ok )) || back "brief.txt has no graduation candidates line"
systemctl is-active farm-dash.service >/dev/null || back "farm-dash is not active"
echo "  farm-dash active; brief.txt:"
grep -E '^(live PnL since promotion|grad bots live|  grad |graduation candidates|  - |  one condition short|  note: no send_result)' "$tmp/brief.txt" | sed 's/^/    /'

echo "== sha256 (expected = patched copy checked above / installed)"
echo "  farm-dash  $(sha "$tmp/farm-dash")"
echo "             $(sha $F)"
echo "Installed phase 16d."
echo "To undo: cp -a /opt/farm/bin/.farm-dash.bak-16d $F && systemctl restart farm-dash"
