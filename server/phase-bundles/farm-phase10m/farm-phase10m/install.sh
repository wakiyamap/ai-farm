#!/usr/bin/env bash
# Phase 10m (2026-11-12): two sentences in /srv/farm/prompts/common.md, asked for by meta after it
# applied decision 2026-11-12-morpho-stop-researcher-runs to the role files:
#  - Workspace table: inbox/live is read only when the watchdog wakes the live-operator;
#    non-urgent reports go to inbox/meta (item 5)
#  - Principle 2: taken in the price-update block, or within seconds to 1-2 blocks of becoming
#    eligible, counts as a latency race (item 2)
# Every prompt is assembled again; if any instance no longer fits its size limit, common.md is
# restored. Nothing is restarted (sessions read the prompt when they start). Backup:
# /srv/farm/prompts/.common.md.bak-10m. Safe to re-run.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
C=/srv/farm/prompts/common.md
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "== patch texts"
python3 -I -B patch-10m.py check "$C"
python3 -I -B patch-10m.py apply "$C" "$tmp" >/dev/null
echo "  common.md: $(stat -c %s "$C") -> $(stat -c %s "$tmp/common.md") bytes"

echo "== backup and install"
[[ -e /srv/farm/prompts/.common.md.bak-10m ]] || cp -a "$C" /srv/farm/prompts/.common.md.bak-10m
cp -a "$C" "$tmp/common.md.before"
install -o "$(stat -c %u "$C")" -g "$(stat -c %g "$C")" -m "$(stat -c %a "$C")" "$tmp/common.md" "$C"

assemble_all() {
  local bad=0 inst
  while read -r inst _; do
    [[ -z "$inst" || "$inst" == \#* ]] && continue
    if "$B/assemble-prompt" "$inst"; then
      echo "  $inst: $(stat -c %s "/srv/farm/runners/$inst/prompt.md") bytes"
    else
      echo "  $inst: FAILED (see the line above)"
      bad=1
    fi
  done < /etc/farm/roles.conf
  return $bad
}

echo "== assemble every instance (warn above 56000, limit 60000)"
if ! assemble_all; then
  echo "!! an instance no longer fits - restoring common.md and assembling again" >&2
  cp -a "$tmp/common.md.before" "$C"
  assemble_all || true
  exit 1
fi
{ ls /srv/farm/ws/inbox/meta/prompt-size-*.md 2>/dev/null || true; } | sed 's/^/  note: /'
echo "Installed phase 10m. Paste everything from '== patch texts' down."
