#!/usr/bin/env bash
# Phase 15k (2026-11-21): USDC a bot earned counts as profit when the gate sweeps it.
#  The one-shot oneshot-bundles-rebalance-ethereum (funded with ETH only) swept back 34.61 USDC, but
#  the gate booked PnL for USDC only against a USDC principal: sweep_usdc got usd null, the native leg
#  -3.73 USD, and the daily-loss guard counted a loss where there was a +30.88 USD profit.
#  - gate-ctl (2 text patches): a bot the gate funded with native only has a USDC baseline of 0, so all
#    USDC swept back is profit (sweep and settle_usdc_in_flight).
#  - farm-dash (3 text patches): swept PnL and its 14-day history also sum sweep_usdc records.
#  - fix-15k.py, once: append a sweep_usdc_fix record (+34.6142 USD) to gate.log and, while the UTC day
#    is still 2026-11-20 (until 09:00 JST), correct realized_usd in pnl.json (-3.7294 -> +30.8848).
#  Nothing is sent on chain. farm-dash is restarted. On failure gate-ctl and farm-dash are restored.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
export PYTHONDONTWRITEBYTECODE=1
G=/opt/farm/bin/gate-ctl; D=/opt/farm/bin/farm-dash; S=/var/lib/farmgate
REF_G=b8fded9fd31c403aad5209af9e3bf0b9d562dc98a90ea72cac43e7b88f11e7d8   # sent 2026-11-21 07:51 JST
REF_D=b366e5e42a2b8daa3f81549cded0506006d3b406485fafbe000b39a47fab85fe   # 15j
sha() { sha256sum "$1" | cut -d' ' -f1; }
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "== checks (nothing is changed yet)"
for f in patch-15k.py test-15k.py fix-15k.py; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$f"
done
echo "  sha256 (reference / installed)"
echo "  gate-ctl   $REF_G"; echo "             $(sha $G)"
echo "  farm-dash  $REF_D"; echo "             $(sha $D)"
python3 -I -B patch-15k.py apply $G $D "$tmp"
for f in gate-ctl farm-dash; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$tmp/$f"
done
echo "== offline tests (installed files: report only, 4 of 7 before 15k)"
python3 -B test-15k.py $G $D fix-15k.py --old 2>/dev/null | tail -1
echo "== offline tests (new files)"
python3 -B test-15k.py "$tmp/gate-ctl" "$tmp/farm-dash" fix-15k.py | grep -v '^ok swept'
echo "== the one-time correction (dry run)"
runuser -u farmgate -- python3 -I -B fix-15k.py check $S

back() {
  echo "!! $1 - restoring gate-ctl and farm-dash" >&2
  [[ -f /opt/farm/bin/.gate-ctl.bak-15k ]] && cp -a /opt/farm/bin/.gate-ctl.bak-15k $G
  [[ -f /opt/farm/bin/.farm-dash.bak-15k ]] && cp -a /opt/farm/bin/.farm-dash.bak-15k $D
  systemctl restart farm-dash.service || true
  exit 1
}

echo "== install"
for f in $G $D; do
  b=$(basename $f)
  [[ -e /opt/farm/bin/.$b.bak-15k ]] || cp -a $f /opt/farm/bin/.$b.bak-15k
  install -o "$(stat -c %u $f)" -g "$(stat -c %g $f)" -m "$(stat -c %a $f)" "$tmp/$b" $f
  echo "  $f"
done
runuser -u farmgate -- /opt/farm/bin/gate-ctl status >/dev/null || back "gate-ctl status fails"
echo "  gate-ctl status ok"
echo "== the one-time correction"
runuser -u farmgate -- python3 -I -B fix-15k.py apply $S
systemctl restart farm-dash.service
ok=0
for _ in $(seq 1 30); do
  if curl -s -m 90 http://127.0.0.1:8090/brief.txt -o "$tmp/brief.txt" && grep -q '^live PnL since promotion' "$tmp/brief.txt"; then ok=1; break; fi
  sleep 2
done
(( ok )) || back "farm-dash brief.txt does not come back"
grep -E '^(capital|live PnL since promotion|swept today)' "$tmp/brief.txt" | sed 's/^/  /'

echo "== sha256 (expected = patched copy checked above / installed)"
for f in $G $D; do echo "  $(basename $f)"; echo "    $(sha "$tmp/$(basename $f)")"; echo "    $(sha $f)"; done
echo "Installed phase 15k."
echo "To undo: cp -a /opt/farm/bin/.gate-ctl.bak-15k $G; cp -a /opt/farm/bin/.farm-dash.bak-15k $D; systemctl restart farm-dash"
echo "(the gate.log sweep_usdc_fix record and the pnl.json correction stay; they are the true figures)"
