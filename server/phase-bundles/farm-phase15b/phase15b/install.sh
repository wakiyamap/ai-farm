#!/usr/bin/env bash
# Phase 15b (2026-11-18):
#  - gate-ctl (2 text patches): the executor deployment goes through send_deploy(), which waits
#    until the bot wallet can pay for it and resends the same signed bytes while the node answers
#    "insufficient funds" (trial-aave-optimism, 2026-11-17 20:21Z: funding receipt seen, deployment
#    refused with "have 0"). Gives up after a minute with nothing sent from the bot key.
#  - run-role (1 text patch): paper-reviewer-claude may run `paper stop <id>`.
#  - decisions/human/2026-11-18-park-approved-trials.md and a note for meta.
# No service restart: gate-ctl is read on every call, run-role at every session start.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
WS=/srv/farm/ws
export PYTHONDONTWRITEBYTECODE=1
sha() { sha256sum "$1" | cut -d' ' -f1; }
GATE_12D=dc0d8d5a64d2b70b874576d1c2b0d9b1fad95285fa9681127dca7853d9430828   # gate-ctl after 12d
RUN_14D=6229fed446698cd92991f9df9aa6460c0504eb628ffa4901365249e622c663ac    # run-role after 14d
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "== checks (nothing is changed yet)"
for f in patch-15b.py test-15b.py; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$f"
done
hg=$(sha $B/gate-ctl); hr=$(sha $B/run-role)
echo "  sha256 now (reference / installed)"
echo "    gate-ctl  $GATE_12D (12d)"
echo "              $hg"
echo "    run-role  $RUN_14D (14d)"
echo "              $hr"
if grep -q 'def send_deploy' $B/gate-ctl && grep -qF 'Bash(paper stop *)' $B/run-role; then
  echo "  gate-ctl and run-role are already the 15b versions"
  cp $B/gate-ctl $B/run-role "$tmp/"
  done_code=1
else
  [[ $hg == "$GATE_12D" ]] || echo "  note: gate-ctl differs from the 12d version; the text patches decide (each must match exactly once)"
  [[ $hr == "$RUN_14D" ]] || echo "  note: run-role differs from the 14d version; the text patch decides"
  python3 -I -B patch-15b.py check $B/gate-ctl $B/run-role
  python3 -I -B patch-15b.py apply $B/gate-ctl $B/run-role "$tmp"
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$tmp/gate-ctl"
  bash -n "$tmp/run-role"
  echo "== offline tests (installed files: report only, 0 of 6 pass before 15b)"
  python3 -I -B test-15b.py $B/gate-ctl $B/run-role --old | tail -1
  done_code=0
fi
echo "== offline tests (patched files)"
python3 -I -B test-15b.py "$tmp/gate-ctl" "$tmp/run-role"
NEW_GATE=$(sha "$tmp/gate-ctl"); NEW_RUN=$(sha "$tmp/run-role")

if [[ $done_code == 0 ]]; then
  echo "== install"
  [[ -e $B/.gate-ctl.bak-15b ]] || cp -a $B/gate-ctl $B/.gate-ctl.bak-15b
  [[ -e $B/.run-role.bak-15b ]] || cp -a $B/run-role $B/.run-role.bak-15b
  put() { install -o "$(stat -c %u "$2")" -g "$(stat -c %g "$2")" -m "$(stat -c %a "$2")" "$1" "$2"; }
  put "$tmp/gate-ctl" $B/gate-ctl
  put "$tmp/run-role" $B/run-role
fi

echo "== gate status"
if ! sudo -u harness /opt/farm/bin/gate status > "$tmp/status.out"; then
  echo "!! gate status failed - restoring gate-ctl and run-role" >&2
  [[ -f $B/.gate-ctl.bak-15b ]] && cp -a $B/.gate-ctl.bak-15b $B/gate-ctl
  [[ -f $B/.run-role.bak-15b ]] && cp -a $B/.run-role.bak-15b $B/run-role
  cat "$tmp/status.out" >&2 || true
  exit 1
fi
python3 -I -B - "$tmp/status.out" <<'PY' || cat "$tmp/status.out"
import json, sys
s = json.load(open(sys.argv[1]))
print("  capital_usd", s.get("capital_usd"), "/", s.get("max_capital_usd"), " frozen", s.get("frozen"), " halted", s.get("halted"),
      " live", len(s.get("live") or {}))
PY

echo "== decision and note for meta"
install -o root -g root -m 644 decision-2026-11-18-park-approved-trials.md $WS/decisions/human/2026-11-18-park-approved-trials.md
install -o root -g root -m 644 inbox-meta-2026-11-18-phase15b-deploy-wait-park.md \
  $WS/inbox/meta/2026-11-18-phase15b-deploy-wait-park.md

echo "== sha256 (expected = patched copy checked above / installed)"
echo "  gate-ctl  $NEW_GATE"
echo "            $(sha $B/gate-ctl)"
echo "  run-role  $NEW_RUN"
echo "            $(sha $B/run-role)"
echo "== paper bots"
for d in "$WS"/bots/paper/*/; do
  id=$(basename "$d")
  dec=$(grep -i -m1 'decision:' "$d/review.md" 2>/dev/null | sed 's/.*decision: *//I' | cut -c1-90 || true)
  printf '  %-30s %-9s %s\n' "$id" "$(systemctl is-active "paper@$id.service" 2>/dev/null || true)" "${dec:-no review}"
done
echo "Installed phase 15b. The reviewers park approved trials from their next run (decision file)."
echo "To undo: sudo cp -a $B/.gate-ctl.bak-15b $B/gate-ctl; sudo cp -a $B/.run-role.bak-15b $B/run-role"
