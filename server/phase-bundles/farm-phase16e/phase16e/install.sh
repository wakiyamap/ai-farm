#!/usr/bin/env bash
# Phase 16e (2026-11-24):
#  - scout-1..4: Qwen (dsh, user earner) -> codex gpt-6-sol (user harness). roles.conf column 3/4 and the
#    agent@scout-N drop-in (no qwen-server dependency, no dsh bind mounts, same 35-minute sessions)
#  - builder-codex retired: farm-builder-codex.timer disabled (unit and roles.conf line kept)
#  - paper-reviewer-claude retired: farm-paper-reviewer-claude.timer disabled (unit and roles.conf line kept);
#    /opt/farm/context/paper-reviewer no longer routes Codex-built bots away, so paper-reviewer reviews all bots
#  - a note for meta
# qwen-server is not touched (stop or repurpose it yourself). run-role, gate, signer, watchdog, relay,
# role files and the scout queue programs are not touched.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
# Running Qwen scout sessions are not killed; they finish (at most 35 min) and the next start uses codex.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
S=/etc/systemd/system; C=/opt/farm/context; RC=/etc/farm/roles.conf
MODEL=gpt-6-sol
BAK=/etc/farm/bak-16e
sha() { sha256sum "$1" | cut -d' ' -f1; }

echo "== checks (nothing is changed yet)"
bash test-16e.sh context-paper-reviewer units/scout.conf
for n in 1 2 3 4; do
  grep -qE "^scout-$n[[:space:]]+scout[[:space:]]+(dsh|codex)[[:space:]]" $RC || { echo "  roles.conf has no scout-$n line" >&2; exit 1; }
  [[ -f $S/agent@scout-$n.service.d/scout.conf ]] || { echo "  $S/agent@scout-$n.service.d/scout.conf missing" >&2; exit 1; }
done
[[ -x $C/paper-reviewer.base ]] || { echo "  $C/paper-reviewer.base missing (14a wrapper not installed?)" >&2; exit 1; }
grep -q 'farm-phase14a-reviewer-routing' $C/paper-reviewer || { echo "  $C/paper-reviewer is not the 14a wrapper; check by hand" >&2; exit 1; }
id -nG harness | grep -qw farm || { echo "  user harness is not in group farm" >&2; exit 1; }
. /etc/farm/farm.env
echo "  smoke test: codex exec -m $MODEL (as harness)"
out=$(cd /srv/farm/ws && sudo -u harness env PATH="$HARNESS_PATH" "$CODEX_BIN" exec --skip-git-repo-check -m "$MODEL" \
      'Reply with the single word OK.' 2>&1 | tail -5) || true
grep -q "OK" <<<"$out" || { echo "$out"; echo "  model $MODEL did not answer as harness; nothing was changed" >&2; exit 1; }
echo "  codex answered"

echo "== backups ($BAK)"
install -d -m 700 $BAK
[[ -e $BAK/roles.conf ]] || cp -a $RC $BAK/roles.conf
[[ -e $BAK/context-paper-reviewer ]] || cp -a $C/paper-reviewer $BAK/context-paper-reviewer
for n in 1 2 3 4; do
  [[ -e $BAK/scout-$n.conf ]] || cp -a $S/agent@scout-$n.service.d/scout.conf $BAK/scout-$n.conf
done

echo "== scouts -> codex $MODEL"
for n in 1 2 3 4; do
  sed -i -E "s/^(scout-$n)[[:space:]]+scout[[:space:]]+[a-z]+[[:space:]]+.*/\1\tscout\tcodex\t$MODEL/" $RC
  install -o root -g root -m 644 units/scout.conf $S/agent@scout-$n.service.d/scout.conf
done
grep -E '^scout-' $RC | sed 's/^/  /'
# queue files were written by earner; make sure harness (group farm) can rewrite them
chmod -R g+rwX /srv/farm/ws/scout

echo "== reviewer: one instance reviews every bot"
install -o root -g root -m 755 context-paper-reviewer $C/paper-reviewer

echo "== retire builder-codex and paper-reviewer-claude (timers only; a running session finishes)"
systemctl disable --now farm-builder-codex.timer farm-paper-reviewer-claude.timer

systemctl daemon-reload
for n in 1 2 3 4; do
  u=$(systemctl show "agent@scout-$n.service" -p User --value)
  [[ $u == harness ]] || { echo "  !! agent@scout-$n runs as '$u', expected harness" >&2; exit 1; }
  /opt/farm/bin/assemble-prompt "scout-$n"
  systemctl reset-failed "agent@scout-$n.service" 2>/dev/null || true
done

echo "== note for meta"
install -o root -g farm -m 644 inbox-meta-2026-11-24-phase16e-codex-scouts.md /srv/farm/ws/inbox/meta/2026-11-24-phase16e-codex-scouts.md

echo "== state"
echo "  sha256 (expected / installed)"
echo "    context/paper-reviewer $(sha context-paper-reviewer)"
echo "                           $(sha $C/paper-reviewer)"
echo "    scout.conf             $(sha units/scout.conf)"
echo "                           $(sha $S/agent@scout-1.service.d/scout.conf)"
systemctl is-enabled farm-builder-codex.timer farm-paper-reviewer-claude.timer 2>/dev/null | sed 's/^/  timers (builder-codex, paper-reviewer-claude): /' || true
for n in 1 2 3 4; do echo "  agent@scout-$n: $(systemctl is-active agent@scout-$n.service || true)"; done
echo "  queue: $(ls /srv/farm/ws/scout/queue | grep -c json || true) candidates"
echo "Installed phase 16e. Scout sessions still running on Qwen finish first; the next ones use codex."
echo "To free Qwen now: sudo systemctl stop agent@scout-{1,2,3,4}.service  (their candidates go back to the queue after 45 min)"
