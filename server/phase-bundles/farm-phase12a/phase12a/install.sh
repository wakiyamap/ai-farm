#!/usr/bin/env bash
# Phase 12a: a second earner instance in a "measure" lane, and decision
# 2026-11-15-widen-beyond-liquidations applied to earner.md and researcher.md.
#  - roles.conf: earner-measure  earner  dsh  qwen3.8-flash-next (same role file, user and model)
#  - agent@earner-measure.service.d/: the earner-local drop-ins with this instance's prompt path
#  - /opt/farm/context/earner: prints the lane and a lane-specific lead list
#  - roles/earner.md, roles/researcher.md: edited copies of the files as they were on
#    2026-11-15 12:59 JST. If meta changed either file since, this script stops before
#    changing anything; send the current files and the bundle is rebuilt.
# gate, signer, watchdog, relay and common.md are not touched.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }

R=/srv/farm/prompts/roles
INST=earner-measure
D=/etc/systemd/system/agent@$INST.service.d
sha() { sha256sum "$1" | cut -d' ' -f1; }

# expected "before" and "after" hashes
OLD_EARNER=86463c98ff1f6fdd54e020f8331c22ec72f77af75c3b21ed94ed443e8f68c675
OLD_RESEARCHER=224bb4ca50395d5f30f53f98bf287c178043c010c032652d178db61454f5bf24
OLD_CONTEXT=d1324631a51dcbc6ee7578779a0f764f6d2b7a16373ada4833871a196e1f9337
NEW_EARNER=$(sha new/earner.md)
NEW_RESEARCHER=$(sha new/researcher.md)
NEW_CONTEXT=$(sha context-earner)

echo "== checks (nothing is changed yet)"
bash -n context-earner
check() {  # $1 installed file, $2 old hash, $3 new hash
  local h; h=$(sha "$1")
  if [[ $h == "$3" ]]; then echo "  $1: already the new version"
  elif [[ $h == "$2" ]]; then echo "  $1: as expected"
  else echo "  $1 changed since the bundle was built (sha256 $h). Nothing was changed." >&2; exit 1
  fi
}
check "$R/earner.md" "$OLD_EARNER" "$NEW_EARNER"
check "$R/researcher.md" "$OLD_RESEARCHER" "$NEW_RESEARCHER"
check /opt/farm/context/earner "$OLD_CONTEXT" "$NEW_CONTEXT"
for u in agent@earner-local agent@$INST; do
  systemctl cat "$u.service" >/dev/null 2>&1 || true
done
id earner >/dev/null
[[ -f /etc/farm/earner-headless.patch.yml ]]

echo "== role files"
for f in earner researcher; do
  if [[ $(sha "$R/$f.md") != $(sha "new/$f.md") ]]; then
    cp -a "$R/$f.md" "$R/.$f.md.bak-12a"
    install -o harness -g harness -m 644 "new/$f.md" "$R/$f.md"
  fi
done

echo "== context script"
if [[ $(sha /opt/farm/context/earner) != "$NEW_CONTEXT" ]]; then
  cp -a /opt/farm/context/earner /opt/farm/context/.earner.bak-12a
  install -o root -g root -m 755 context-earner /opt/farm/context/earner
fi

echo "== roles.conf"
if ! grep -qE "^$INST[[:space:]]" /etc/farm/roles.conf; then
  cp -a /etc/farm/roles.conf /etc/farm/roles.conf.bak-12a
  printf '%s\t%s\t%s\t%s\n' "$INST" earner dsh qwen3.8-flash-next >> /etc/farm/roles.conf
fi
grep -E '^earner' /etc/farm/roles.conf

echo "== unit drop-ins"
install -d -o root -g root -m 755 "$D"
install -o root -g root -m 644 units/boot.conf units/earner.conf "$D/"
systemctl daemon-reload

echo "== assembled prompts (limit 60000, keep at or under 56000)"
for i in earner-local "$INST" researcher-codex researcher-claude; do
  /opt/farm/bin/assemble-prompt "$i"
  n=$(stat -c %s "/srv/farm/runners/$i/prompt.md")
  echo "  $i: $n bytes"
  (( n <= 56000 )) || { echo "  $i is over 56000 bytes" >&2; exit 1; }
done

echo "== lane lines"
for i in earner-local "$INST"; do
  printf '  %s -> ' "$i"
  runuser -u earner -- /opt/farm/context/earner "$i" 2>/dev/null | grep -m1 '^- lane:' || echo "(no lane line)"
done

echo "== note for meta"
install -o root -g root -m 644 inbox-meta-2026-11-15-phase12a-measure-lane.md \
  /srv/farm/ws/inbox/meta/2026-11-15-phase12a-measure-lane.md

echo "== start"
systemctl enable --now "agent@$INST.service"
sleep 3
systemctl --no-pager --lines=0 status "agent@$INST.service" | head -4 || true
echo "Installed phase 12a. agent@earner-local keeps its old prompt until its next session starts."
echo "To undo: systemctl disable --now agent@$INST; restore the .bak-12a files; remove the $INST line from roles.conf; rm -r $D; systemctl daemon-reload"
