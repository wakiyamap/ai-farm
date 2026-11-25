#!/usr/bin/env bash
# Phase 13b: widen the Bash list of the claude-harness earner (earner-claude) in run-role.
# Adds mkdir (any path), cd, sed, awk, sort, uniq, cut, tr, echo, printf, find, diff, tee.
# Reason: in its first session two Bash calls were refused (a relative mkdir, a pipeline with sed).
# Nothing else changes. Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
export PYTHONDONTWRITEBYTECODE=1
sha() { sha256sum "$1" | cut -d' ' -f1; }
OLD_RUN=9a56b50a157f141cc728868a3987cb0e47a889d355e80c1dd97db2007a0b623b
NEW_RUN=c355840c1a470b6970ef930250b543b8830ea0ea7d721615c0c07a275791c058
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
echo "== checks (nothing is changed yet)"
hr=$(sha $B/run-role)
if [[ $hr == "$NEW_RUN" ]]; then echo "  run-role is already the 13b version"; exit 0; fi
if [[ $hr != "$OLD_RUN" ]]; then
  echo "  run-role changed since the bundle was built. Nothing was changed." >&2
  echo "    expected $OLD_RUN" >&2
  echo "    got      $hr" >&2
  exit 1
fi
python3 -I -B patch-13b.py check $B/run-role
python3 -I -B patch-13b.py apply $B/run-role "$tmp/run-role"
bash -n "$tmp/run-role"
[[ $(sha "$tmp/run-role") == "$NEW_RUN" ]] || { echo "  unexpected sha256 after patching; nothing was changed" >&2; exit 1; }
for want in 'Bash(mkdir *)' 'Bash(sed *)' 'Bash(paper start *)'; do
  grep -qF "$want" "$tmp/run-role" || { echo "  missing $want; nothing was changed" >&2; exit 1; }
done
for deny in 'Bash(gate promote *),Bash(paper start' 'Bash(rm *)' 'Bash(bash *)'; do
  sed -n '/^    earner)$/,/;;$/p' "$tmp/run-role" | grep -qF "$deny" && { echo "  earner must not have $deny" >&2; exit 1; }
done
echo "  patched copy ok"
echo "== run-role"
[[ -e $B/.run-role.bak-13b ]] || cp -a $B/run-role $B/.run-role.bak-13b
install -o root -g root -m 755 "$tmp/run-role" $B/run-role
echo "  sha256 (expected / installed)"
echo "    run-role $NEW_RUN"
echo "             $(sha $B/run-role)"
echo "Installed phase 13b. earner-claude uses the new list from its next session."
echo "To undo: sudo cp -a $B/.run-role.bak-13b $B/run-role"
