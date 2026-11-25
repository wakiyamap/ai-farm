#!/usr/bin/env bash
# Phase 14b: four Qwen scouts and the candidate queue.
#  - roles/scout.md (new); instances scout-1..4 (dsh, qwen3.8-flash-next, user earner), 20-minute sessions
#  - /opt/farm/context/scout (takes one candidate), /opt/farm/bin/scout-enum (fills the queue),
#    /opt/farm/bin/scout-done (closes a candidate)
#  - /srv/farm/ws/scout/{queue,doing,done} (group farm)
#  - farm-scout-enum.service/.timer (every 2 h), farm-scout@.timer (one per scout)
#  - agent@earner-local and agent@earner-measure stopped and disabled (units and earner.md kept)
#  - a note for meta
# run-role, gate, signer, watchdog, relay, common.md and the builders are not touched.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin; C=/opt/farm/context; R=/srv/farm/prompts/roles; S=/etc/systemd/system
SW=/srv/farm/ws/scout
N=(1 2 3 4)

echo "== checks (nothing is changed yet)"
for f in scout-enum scout-done context-scout; do python3 -I -B -c 'import sys; compile(open(sys.argv[1]).read(), sys.argv[1], "exec")' "$f"; done
bash -n test-14b.sh
id earner >/dev/null
id -nG earner | grep -qw farm || { echo "  user earner is not in group farm" >&2; exit 1; }
[[ -f /etc/farm/earner-headless.patch.yml ]] || { echo "  /etc/farm/earner-headless.patch.yml missing" >&2; exit 1; }
grep -qE '^earner-local[[:space:]]' /etc/farm/roles.conf || { echo "  roles.conf has no earner-local line" >&2; exit 1; }
systemctl cat qwen-server.service >/dev/null 2>&1 || { echo "  qwen-server.service not found" >&2; exit 1; }
if [[ -e $R/scout.md ]] && ! cmp -s $R/scout.md new/scout.md; then
  echo "  $R/scout.md exists and differs from this bundle. Nothing was changed." >&2; exit 1
fi
echo "== offline tests"
bash test-14b.sh scout-enum context-scout scout-done

echo "== programs, role file, queue directories"
install -o root -g root -m 755 scout-enum scout-done $B/
install -o root -g root -m 755 context-scout $C/scout
install -o harness -g harness -m 644 new/scout.md $R/scout.md
for d in "$SW" "$SW/queue" "$SW/doing" "$SW/done"; do
  install -d -o harness -g farm -m 2775 "$d"
  setfacl -m g:farm:rwx -m d:g:farm:rwX -m m::rwx -m d:m::rwx "$d"
done

echo "== roles.conf"
[[ -e /etc/farm/roles.conf.bak-14b ]] || cp -a /etc/farm/roles.conf /etc/farm/roles.conf.bak-14b
for n in "${N[@]}"; do
  grep -qE "^scout-$n[[:space:]]" /etc/farm/roles.conf || printf 'scout-%s\tscout\tdsh\tqwen3.8-flash-next\n' "$n" >> /etc/farm/roles.conf
done
grep -E '^(scout|earner)' /etc/farm/roles.conf | sed 's/^/  /'

echo "== units"
for n in "${N[@]}"; do
  install -d -o root -g root -m 755 "$S/agent@scout-$n.service.d"
  sed "s/@INST@/scout-$n/" units/scout.conf.in > "$S/agent@scout-$n.service.d/scout.conf"
  chmod 644 "$S/agent@scout-$n.service.d/scout.conf"
done
install -o root -g root -m 644 units/farm-scout@.timer units/farm-scout-enum.service units/farm-scout-enum.timer $S/
systemctl daemon-reload
for n in "${N[@]}"; do
  u=$(systemctl show "agent@scout-$n.service" -p User --value)
  [[ $u == earner ]] || { echo "  !! agent@scout-$n would run as '${u:-root}'; nothing enabled" >&2; exit 1; }
done
echo "  agent@scout-1..4 run as earner, cut-off $(systemctl show agent@scout-1.service -p RuntimeMaxUSec --value)"

echo "== assembled prompts (limit 60000)"
for n in "${N[@]}"; do
  $B/assemble-prompt "scout-$n"
done
echo "  scout: $(stat -c %s /srv/farm/runners/scout-1/prompt.md) bytes"

echo "== first queue fill (as earner, takes up to a minute)"
systemctl start farm-scout-enum.service || true
journalctl -u farm-scout-enum.service -n 8 --no-pager -o cat | sed 's/^/  /'
echo "  queue: $(ls $SW/queue | grep -c json) candidates; first five:"
ls $SW/queue | head -5 | sed 's/^/    /'

echo "== note for meta"
install -o root -g root -m 644 inbox-meta-2026-11-17-phase14b-scouts.md /srv/farm/ws/inbox/meta/2026-11-17-phase14b-scouts.md

echo "== switch earners -> scouts"
for i in earner-local earner-measure; do
  systemctl disable --now "agent@$i.service" 2>/dev/null && echo "  stopped and disabled agent@$i" || echo "  agent@$i: already off"
done
systemctl enable --now farm-scout-enum.timer
for n in "${N[@]}"; do systemctl enable --now "farm-scout@$n.timer"; done
systemctl list-timers 'farm-scout*' --no-pager | head -7
echo "Installed phase 14b. The first scout sessions start within a minute or two."
echo "To undo: disable farm-scout@1..4.timer and farm-scout-enum.timer; systemctl enable --now agent@earner-local agent@earner-measure;"
echo "         restore /etc/farm/roles.conf.bak-14b; rm -r $S/agent@scout-*.service.d; systemctl daemon-reload"
