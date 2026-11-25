#!/usr/bin/env bash
# Phase 11d (2026-11-14): the earner prompt, tightened at the human's request.
#  - /srv/farm/prompts/roles/earner.md is replaced by a rewritten file (same rules, the five
#    repeated mistakes first, one ordered target list, the reaction-time race rule of decision
#    2026-11-14-race-rule-seconds)
#  - /srv/farm/prompts/common.md: the chain paragraph becomes a short list, Principle 2 states the
#    race rule by reaction time
# Each file is replaced only if the installed one is exactly the version this was written
# against (sha256 below) - meta edits earner.md, so a newer one is left alone and the install
# stops before changing anything. Every prompt is assembled again; if any instance fails, both
# files are restored. Nothing is restarted (a session reads its prompt when it starts).
# Backups: /srv/farm/prompts/.common.md.bak-11d, /srv/farm/prompts/roles/.earner.md.bak-11d.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin P=/srv/farm/prompts
C=$P/common.md E=$P/roles/earner.md
OLD_C=58f561644eb63534ea0cbf88cd0565e7ea6d7b8cddb80f722d20f849b1ab3700
OLD_E=c1eb37f4e861d2707e7e25ef107fdb1c0737485af24cf5cee61578e29efa00a0
NEW_C=2d91d488a8ba8bb8428c78e5cbf5241474dd0a8bac22c800c36b85239613e875
NEW_E=ca0e422985f31242cf89cd2cf03017b95796f1c75a001d1eaa743903fdcae88a
sha() { sha256sum "$1" | cut -d' ' -f1; }
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "== check the installed files"
[[ "$(sha new/common.md)" == "$NEW_C" && "$(sha new/earner.md)" == "$NEW_E" ]] || { echo "the bundle's own files do not match" >&2; exit 1; }
todo=()
for pair in "$C:$OLD_C:$NEW_C:common.md" "$E:$OLD_E:$NEW_E:earner.md"; do
  IFS=: read -r path old new name <<<"$pair"
  have=$(sha "$path")
  if [[ "$have" == "$new" ]]; then
    echo "  $name: already the 11d version"
  elif [[ "$have" == "$old" ]]; then
    echo "  $name: $(stat -c %s "$path") -> $(stat -c %s "new/$name") bytes"
    todo+=("$path:$name")
  else
    echo "!! $name was changed since this bundle was written (sha256 $have). Nothing was changed." >&2
    echo "   Send the current file to the chat: sudo cat $path" >&2
    exit 1
  fi
done

sizes() {
  local bad=0 inst
  while read -r inst _; do
    [[ -z "$inst" || "$inst" == \#* ]] && continue
    if "$B/assemble-prompt" "$inst"; then
      echo "  $inst: $(stat -c %s "/srv/farm/runners/$inst/prompt.md") bytes"
    else
      echo "  $inst: FAILED (see the line above)"; bad=1
    fi
  done < /etc/farm/roles.conf
  return $bad
}

echo "== prompt sizes before"
sizes || true

if (( ${#todo[@]} )); then
  echo "== backup and install"
  for t in "${todo[@]}"; do
    IFS=: read -r path name <<<"$t"
    bak="$(dirname "$path")/.$name.bak-11d"
    [[ -e "$bak" ]] || cp -a "$path" "$bak"
    cp -a "$path" "$tmp/$name.before"
    install -o "$(stat -c %u "$path")" -g "$(stat -c %g "$path")" -m "$(stat -c %a "$path")" "new/$name" "$path"
  done
  echo "== prompt sizes after (warn above 56000, limit 60000)"
  if ! sizes; then
    echo "!! an instance no longer assembles - restoring both files" >&2
    for t in "${todo[@]}"; do
      IFS=: read -r path name <<<"$t"
      cp -a "$tmp/$name.before" "$path"
    done
    sizes || true
    exit 1
  fi
fi

note=/srv/farm/ws/inbox/meta/2026-11-14-phase11d-earner-prompt.md
[[ -e $note ]] || install -o harness -g "$(stat -c %G /srv/farm/ws/inbox/meta)" -m 664 inbox-meta-2026-11-14-phase11d-earner-prompt.md "$note"
echo "Installed phase 11d. Paste everything from '== check the installed files' down."
