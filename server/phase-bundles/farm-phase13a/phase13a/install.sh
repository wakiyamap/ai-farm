#!/usr/bin/env bash
# Phase 13a: the earner role on Claude, as a third earner instance, for a one-day measurement.
#  - roles.conf: earner-claude  earner  claude  <model>   (same role file as the Qwen earners;
#    OS user harness; /opt/farm/context/earner gives it the build lane)
#  - run-role (1 text patch): a tool list for a claude-harness earner (write bots/paper and claims,
#    start a paper bot, python3 / node / forge). No gate promote, no paper archive.
#  - agent@earner-claude.service.d/session.conf: 75-minute cut-off, like the other earners
#  - farm-earner-claude.timer: 8 sessions a day (00:40 JST and every 3 hours)
#  - a note for meta
# The model defaults to opus (what researcher-claude and meta already use). To use another one:
#     sudo MODEL=<name as the claude /model picker shows it> ./install.sh
# In -p sessions Claude Code bills usage credits without asking when a model is outside the plan's
# included limit, so check the model in an interactive session first.
# earner.md, common.md, gate, signer, watchdog, relay and the Qwen earners are not touched.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
INST=earner-claude
MODEL="${MODEL:-opus}"
D=/etc/systemd/system/agent@$INST.service.d
T=/etc/systemd/system/farm-$INST.timer
export PYTHONDONTWRITEBYTECODE=1
sha() { sha256sum "$1" | cut -d' ' -f1; }
OLD_RUN=594c299e5ae8573281e7135bfc4f91321da5b4d9808c65226ccda0b610bbd1c9
NEW_RUN=9a56b50a157f141cc728868a3987cb0e47a889d355e80c1dd97db2007a0b623b
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "== checks (nothing is changed yet)"
[[ "$MODEL" =~ ^[A-Za-z0-9._\[\]-]+$ ]] || { echo "  MODEL must be one word (got: $MODEL)" >&2; exit 1; }
echo "  model: $MODEL"
id harness >/dev/null
[[ -x /opt/farm/context/earner ]] || { echo "  /opt/farm/context/earner is missing" >&2; exit 1; }
grep -qE '^earner-local[[:space:]]+earner[[:space:]]' /etc/farm/roles.conf \
  || { echo "  roles.conf has no earner-local line; this is not the farm host?" >&2; exit 1; }
python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' patch-13a.py
bash -n test-13a.sh
hr=$(sha $B/run-role)
if [[ $hr == "$NEW_RUN" ]]; then
  echo "  run-role is already the 13a version"
  cp $B/run-role "$tmp/run-role"
elif [[ $hr == "$OLD_RUN" ]]; then
  echo "  run-role: as expected"
  python3 -I -B patch-13a.py check $B/run-role
  python3 -I -B patch-13a.py apply $B/run-role "$tmp/run-role"
  [[ $(sha "$tmp/run-role") == "$NEW_RUN" ]] \
    || { echo "  the patched run-role does not have the expected sha256; nothing was changed" >&2; exit 1; }
else
  echo "  run-role changed since the bundle was built. Nothing was changed." >&2
  echo "    expected $OLD_RUN" >&2
  echo "    got      $hr" >&2
  exit 1
fi
echo "== offline tests"
bash test-13a.sh "$tmp/run-role"

echo "== run-role"
if [[ $hr != "$NEW_RUN" ]]; then
  [[ -e $B/.run-role.bak-13a ]] || cp -a $B/run-role $B/.run-role.bak-13a
  install -o root -g root -m 755 "$tmp/run-role" $B/run-role
fi
echo "  sha256 (expected / installed)"
echo "    run-role $NEW_RUN"
echo "             $(sha $B/run-role)"

echo "== roles.conf"
if grep -qE "^$INST[[:space:]]" /etc/farm/roles.conf; then
  cur=$(awk -v i="$INST" '$1 == i { print $4 }' /etc/farm/roles.conf)
  if [[ $cur != "$MODEL" ]]; then
    cp -a /etc/farm/roles.conf /etc/farm/roles.conf.bak-13a-$(date +%H%M%S)
    sed -i -E "s/^($INST[[:space:]]+earner[[:space:]]+claude[[:space:]]+).*/\1$MODEL/" /etc/farm/roles.conf
    echo "  model changed: $cur -> $MODEL"
  fi
else
  [[ -e /etc/farm/roles.conf.bak-13a ]] || cp -a /etc/farm/roles.conf /etc/farm/roles.conf.bak-13a
  printf '%s\t%s\t%s\t%s\n' "$INST" earner claude "$MODEL" >> /etc/farm/roles.conf
fi
grep -E '^earner' /etc/farm/roles.conf | sed 's/^/  /'

echo "== unit drop-in and timer"
install -d -o root -g root -m 755 "$D"
install -o root -g root -m 644 units/session.conf "$D/"
install -o root -g root -m 644 units/farm-earner-claude.timer "$T"
systemctl daemon-reload
u=$(systemctl show "agent@$INST.service" -p User --value)
if [[ $u != harness ]]; then
  echo "  !! agent@$INST would run as '${u:-root}', not harness. Removing the timer; nothing was started." >&2
  rm -f "$T"; systemctl daemon-reload
  exit 1
fi
echo "  agent@$INST runs as: $u, cut-off $(systemctl show "agent@$INST.service" -p RuntimeMaxUSec --value)"

echo "== assembled prompt"
/opt/farm/bin/assemble-prompt "$INST"
echo "  $INST: $(stat -c %s "/srv/farm/runners/$INST/prompt.md") bytes"
printf '  lane -> '
runuser -u harness -- /opt/farm/context/earner "$INST" 2>/dev/null | grep -m1 '^- lane:' || echo "(no lane line)"

echo "== note for meta"
install -o root -g root -m 644 inbox-meta-2026-11-17-phase13a-earner-claude.md \
  /srv/farm/ws/inbox/meta/2026-11-17-phase13a-earner-claude.md

echo "== timer"
systemctl enable --now "farm-$INST.timer"
systemctl list-timers "farm-$INST.timer" --no-pager | head -3
echo "Installed phase 13a. First session: at the time above (shown in UTC), or now with:"
echo "    sudo systemctl start --no-block agent@$INST"
echo "To pause: sudo systemctl disable --now farm-$INST.timer"
echo "To undo:  the line above; cp -a $B/.run-role.bak-13a $B/run-role; remove the $INST line from"
echo "          /etc/farm/roles.conf; rm -r $D $T; systemctl daemon-reload"
