#!/usr/bin/env bash
# Phase 14a: builders and model-split review.
#  - roles/builder.md (new) and two instances: builder-claude (claude, claude-mythos-5-2) and
#    builder-codex (codex, gpt-6-sol), 8 sessions a day each, 75-minute cut-off
#  - paper-reviewer-claude (claude, opus, same role file), every 90 minutes
#  - /opt/farm/context/builder (new): the earner context plus trial candidates
#  - /opt/farm/context/paper-reviewer: the original moves to paper-reviewer.base and a wrapper routes
#    bots so that no model reviews its own model's work
#  - run-role (1 text patch): the builder role gets the earner's claude tool list
#  - timers disabled (units kept): farm-earner-claude, farm-researcher-claude, farm-researcher-codex
#  - a note for meta
# earner-local / earner-measure (Qwen), gate, signer, watchdog, relay and common.md are not touched.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
C=/opt/farm/context
R=/srv/farm/prompts/roles
S=/etc/systemd/system
export PYTHONDONTWRITEBYTECODE=1
sha() { sha256sum "$1" | cut -d' ' -f1; }
OLD_RUN=c355840c1a470b6970ef930250b543b8830ea0ea7d721615c0c07a275791c058
NEW_RUN=586ca98574b6d091a2c290271cb9f29cc3556362cd475292f11b0d9e1c720bd1
MARKER=farm-phase14a-reviewer-routing
INSTANCES=(builder-claude builder-codex paper-reviewer-claude)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "== checks (nothing is changed yet)"
for f in context-builder context-paper-reviewer test-14a.sh; do bash -n "$f"; done
python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' patch-14a.py
[[ -x $C/earner ]] || { echo "  $C/earner is missing" >&2; exit 1; }
[[ -x $C/paper-reviewer ]] || { echo "  $C/paper-reviewer is missing" >&2; exit 1; }
if [[ -e $R/builder.md ]] && ! cmp -s "$R/builder.md" new/builder.md; then
  echo "  $R/builder.md exists and differs from this bundle (meta may have edited it). Nothing was changed." >&2; exit 1
fi
hr=$(sha $B/run-role)
if [[ $hr == "$NEW_RUN" ]]; then
  echo "  run-role is already the 14a version"; cp $B/run-role "$tmp/run-role"
elif [[ $hr == "$OLD_RUN" ]]; then
  echo "  run-role: as expected"
  python3 -I -B patch-14a.py check $B/run-role
  python3 -I -B patch-14a.py apply $B/run-role "$tmp/run-role"
  [[ $(sha "$tmp/run-role") == "$NEW_RUN" ]] || { echo "  unexpected sha256 after patching; nothing was changed" >&2; exit 1; }
else
  echo "  run-role changed since the bundle was built. Nothing was changed." >&2
  echo "    expected $OLD_RUN" >&2; echo "    got      $hr" >&2; exit 1
fi
echo "== offline tests"
bash test-14a.sh "$tmp/run-role" context-paper-reviewer

echo "== run-role"
if [[ $hr != "$NEW_RUN" ]]; then
  [[ -e $B/.run-role.bak-14a ]] || cp -a $B/run-role $B/.run-role.bak-14a
  install -o root -g root -m 755 "$tmp/run-role" $B/run-role
fi
echo "  sha256 (expected / installed)"
echo "    run-role $NEW_RUN"
echo "             $(sha $B/run-role)"

echo "== role file and context scripts"
install -o harness -g harness -m 644 new/builder.md $R/builder.md
install -o root -g root -m 755 context-builder $C/builder
if grep -q "$MARKER" $C/paper-reviewer; then
  echo "  reviewer routing already installed"
else
  [[ -e $C/paper-reviewer.base ]] && { echo "  $C/paper-reviewer.base exists but the wrapper is not installed; check by hand" >&2; exit 1; }
  cp -a $C/paper-reviewer $C/paper-reviewer.base
fi
install -o root -g root -m 755 context-paper-reviewer $C/paper-reviewer

echo "== roles.conf"
[[ -e /etc/farm/roles.conf.bak-14a ]] || cp -a /etc/farm/roles.conf /etc/farm/roles.conf.bak-14a
add() { grep -qE "^$1[[:space:]]" /etc/farm/roles.conf || printf '%s\t%s\t%s\t%s\n' "$@" >> /etc/farm/roles.conf; }
add builder-claude builder claude claude-mythos-5-2
add builder-codex builder codex gpt-6-sol
add paper-reviewer-claude paper-reviewer claude opus
grep -E '^(builder|paper-reviewer|earner|researcher)' /etc/farm/roles.conf | sed 's/^/  /'

echo "== units"
for i in builder-claude builder-codex; do
  install -d -o root -g root -m 755 "$S/agent@$i.service.d"
  install -o root -g root -m 644 units/session.conf "$S/agent@$i.service.d/"
done
install -o root -g root -m 644 units/farm-builder-claude.timer units/farm-builder-codex.timer units/farm-paper-reviewer-claude.timer $S/
systemctl daemon-reload
for i in "${INSTANCES[@]}"; do
  u=$(systemctl show "agent@$i.service" -p User --value)
  [[ $u == harness ]] || { echo "  !! agent@$i would run as '${u:-root}'; timers not enabled" >&2; exit 1; }
  echo "  agent@$i runs as $u, cut-off $(systemctl show "agent@$i.service" -p RuntimeMaxUSec --value)"
done

echo "== assembled prompts (limit 60000, keep at or under 56000)"
for i in "${INSTANCES[@]}"; do
  /opt/farm/bin/assemble-prompt "$i"
  n=$(stat -c %s "/srv/farm/runners/$i/prompt.md"); echo "  $i: $n bytes"
  (( n <= 56000 )) || { echo "  $i is over 56000 bytes; timers not enabled" >&2; exit 1; }
done

echo "== context smoke test (as harness)"
runuser -u harness -- $C/builder builder-claude 2>&1 | grep -E '^###' | sed 's/^/  /'
for i in paper-reviewer paper-reviewer-claude; do
  echo "  $i:"; runuser -u harness -- $C/paper-reviewer "$i" 2>&1 | grep -E '^\| [a-z0-9]' | sed 's/^/    /'
done

echo "== note for meta"
install -o root -g root -m 644 inbox-meta-2026-11-17-phase14a-builders.md /srv/farm/ws/inbox/meta/2026-11-17-phase14a-builders.md

echo "== timers"
for t in farm-earner-claude farm-researcher-claude farm-researcher-codex; do
  systemctl disable --now "$t.timer" 2>/dev/null && echo "  disabled $t.timer" || echo "  $t.timer: not found or already off"
done
for t in farm-builder-claude farm-builder-codex farm-paper-reviewer-claude; do systemctl enable --now "$t.timer"; done
systemctl list-timers 'farm-builder-*' 'farm-paper-reviewer*' --no-pager | head -6
echo "Installed phase 14a. Sessions now running keep going until they end."
echo "To undo: disable the three new timers; re-enable farm-earner-claude, farm-researcher-claude, farm-researcher-codex;"
echo "         cp -a $B/.run-role.bak-14a $B/run-role; mv $C/paper-reviewer.base $C/paper-reviewer;"
echo "         restore /etc/farm/roles.conf.bak-14a; rm $R/builder.md $C/builder; systemctl daemon-reload"
