#!/usr/bin/env bash
# Phase 15g (2026-11-19): farmbot_signer.send keeps an explicit priority fee of 0 (one text patch in
# /opt/farm/lib/farmbot_signer.py), and a note for meta answering its 11-18 22:xx questions.
# No service is restarted: live bots pick the fix up when they are next started.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
F=/opt/farm/lib/farmbot_signer.py
sha() { sha256sum "$1" | cut -d' ' -f1; }
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
export PYTHONDONTWRITEBYTECODE=1

echo "== checks (nothing is changed yet)"
echo "  farmbot_signer.py now: $(sha $F)"
python3 -I -B test-15g.py
if grep -q 'if max_priority_fee_per_gas is None else' $F; then
  echo "  already the 15g version"; cp $F "$tmp/farmbot_signer.py"; NEW=0
else
  python3 -I -B patch-15g.py check $F
  python3 -I -B patch-15g.py apply $F "$tmp/farmbot_signer.py"
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$tmp/farmbot_signer.py"
  NEW=1
fi
echo "  the changed line:"
grep -n 'max_priority_fee_per_gas' "$tmp/farmbot_signer.py" | sed 's/^/    /'
if (( NEW )); then
  echo "== install"
  [[ -e $F.bak-15g ]] || cp -a $F $F.bak-15g
  install -o "$(stat -c %u $F)" -g "$(stat -c %g $F)" -m "$(stat -c %a $F)" "$tmp/farmbot_signer.py" $F
  runuser -u farmbot -- python3 -I -B -c 'import sys; sys.path.insert(0, "/opt/farm/lib"); import farmbot_signer; print("  farmbot imports the new module: ok")' \
    || { cp -a $F.bak-15g $F; echo "!! farmbot cannot import the patched module; restored" >&2; exit 1; }
fi
install -o root -g root -m 644 inbox-meta-2026-11-19-phase15g-signer-tip.md /srv/farm/ws/inbox/meta/2026-11-19-phase15g-signer-tip.md
echo "== sha256 (expected / installed)"
echo "  farmbot_signer.py $(sha "$tmp/farmbot_signer.py")"
echo "                    $(sha $F)"
echo "Installed phase 15g. Running bots keep the old code until restarted. To undo: sudo cp -a $F.bak-15g $F"
