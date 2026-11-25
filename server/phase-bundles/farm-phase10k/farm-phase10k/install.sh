#!/usr/bin/env bash
# Phase 10k (2026-11-11): assemble-prompt tells meta before a prompt reaches its size limit.
# On 2026-11-11 the earner prompt grew to 61,377 bytes (limit 60,000; dsh reads at most 64 KiB)
# and every earner session failed at start for 1.5 hours before anyone saw why.
#  - above 56,000 bytes: the session starts as before, and assemble-prompt writes
#    inbox/meta/prompt-size-<instance>.md (as harness; rewritten only when the size changes)
#  - above 60,000 bytes: it fails as before, and the note says the instance cannot start
#  - at or under 56,000 bytes: the note is removed
# Nothing is restarted. Backup: /opt/farm/bin/.assemble-prompt.bak-10k. Safe to re-run.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "== patch texts"
python3 -I -B patch-10k.py check "$B/assemble-prompt"
python3 -I -B patch-10k.py apply "$B/assemble-prompt" "$tmp" >/dev/null
bash -n "$tmp/assemble-prompt"
grep -q '^MAX_BYTES=60000 ' "$tmp/assemble-prompt" || { echo "MAX_BYTES is not 60000 in the installed file; set it back first" >&2; exit 1; }
echo "== offline tests (installed file: report only)"
bash test-10k.sh "$B/assemble-prompt" --old || true
echo "== offline tests (patched file)"
bash test-10k.sh "$tmp/assemble-prompt"

echo "== backup and install"
[[ -e "$B/.assemble-prompt.bak-10k" ]] || cp -a "$B/assemble-prompt" "$B/.assemble-prompt.bak-10k"
install -o "$(stat -c %u "$B/assemble-prompt")" -g "$(stat -c %g "$B/assemble-prompt")" -m "$(stat -c %a "$B/assemble-prompt")" "$tmp/assemble-prompt" "$B/assemble-prompt"

echo "== assemble every instance once (sizes; warn above 56000, limit 60000)"
while read -r inst _; do
  [[ -z "$inst" || "$inst" == \#* ]] && continue
  if "$B/assemble-prompt" "$inst"; then
    echo "  $inst: $(stat -c %s "/srv/farm/runners/$inst/prompt.md") bytes"
  else
    echo "  $inst: FAILED (see the line above)"
  fi
done < /etc/farm/roles.conf
ls /srv/farm/ws/inbox/meta/prompt-size-*.md 2>/dev/null | sed 's/^/  note: /' || true
echo "Installed phase 10k. Paste everything from '== patch texts' down."
