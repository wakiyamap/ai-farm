#!/usr/bin/env bash
# Phase 14d: read tools (python3, jq, ls, cat, head, tail, grep, wc, date) for the claude-harness
# paper-reviewer (paper-reviewer-claude) and meta. One run-role text patch; nothing else changes.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
sha() { sha256sum "$1" | cut -d' ' -f1; }
OLD_RUN=586ca98574b6d091a2c290271cb9f29cc3556362cd475292f11b0d9e1c720bd1
NEW_RUN=6229fed446698cd92991f9df9aa6460c0504eb628ffa4901365249e622c663ac
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
hr=$(sha $B/run-role)
if [[ $hr == "$NEW_RUN" ]]; then echo "run-role is already the 14d version"; exit 0; fi
[[ $hr == "$OLD_RUN" ]] || { echo "run-role changed since 14a (sha256 $hr). Nothing was changed." >&2; exit 1; }
python3 -I -B patch-14d.py apply $B/run-role "$tmp/run-role"
bash -n "$tmp/run-role"
[[ $(sha "$tmp/run-role") == "$NEW_RUN" ]] || { echo "unexpected sha256 after patching; nothing was changed" >&2; exit 1; }
[[ -e $B/.run-role.bak-14d ]] || cp -a $B/run-role $B/.run-role.bak-14d
install -o root -g root -m 755 "$tmp/run-role" $B/run-role
echo "sha256 (expected / installed)"
echo "  run-role $NEW_RUN"
echo "           $(sha $B/run-role)"
echo "Installed phase 14d. paper-reviewer-claude and meta get the tools from their next session."
echo "To undo: sudo cp -a $B/.run-role.bak-14d $B/run-role"
