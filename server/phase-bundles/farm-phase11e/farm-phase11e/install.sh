#!/usr/bin/env bash
# Phase 11e (2026-11-14): the rest of the prompts, tightened at the human's request (follows 11d).
#  - roles/TOOLS.md: ten long rows shortened (the call columns are unchanged); the details that
#    left the table are listed in the note for meta, who checks them against the wiki
#  - roles/paper-reviewer.md, roles/researcher.md: the block-count race wording is replaced by
#    the reaction-time rule of decision 2026-11-14-race-rule-seconds; the reviewer's `demote`
#    bullet is moved back to the other decisions
# Each file is replaced only if the installed one is exactly the version this was written
# against; a newer one stops the install before anything changes. Every prompt is assembled
# again; if any instance fails, the files are restored. Nothing is restarted.
# Backups: /srv/farm/prompts/roles/.<name>.bak-11e.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin P=/srv/farm/prompts/roles
sha() { sha256sum "$1" | cut -d' ' -f1; }
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
PAIRS=(
  "TOOLS.md:31150471a19ca69a07d9336002ba8a959d7ada5ed28d2691bbb8025b101b8bc4:3d51378950fbd5a9cadc6ad35c7e10a74535e13bda13dd8c4b351e3ac139c3d6"
  "paper-reviewer.md:69094353a6be96017ab1ccd56b19c826bba8ec70a2d5e378fcd937bbddfe1391:ef9108d22c920b07677839a6b2065b9d039499683a895d33fec7e93c83ca2c81"
  "researcher.md:b296a68adac324f22aad5f505f31ac7662a65a2507d81ec4799eb441e22178b2:09190a36d498d735be856e40970b2be155fc2b19e0b1ef84ff8a78d8f3e0b4f1"
)

echo "== check the installed files"
todo=()
for pair in "${PAIRS[@]}"; do
  IFS=: read -r name old new <<<"$pair"
  path=$P/$name
  [[ "$(sha "new/$name")" == "$new" ]] || { echo "the bundle's own $name does not match" >&2; exit 1; }
  have=$(sha "$path")
  if [[ "$have" == "$new" ]]; then
    echo "  $name: already the 11e version"
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
    bak="$(dirname "$path")/.$name.bak-11e"
    [[ -e "$bak" ]] || cp -a "$path" "$bak"
    cp -a "$path" "$tmp/$name.before"
    install -o "$(stat -c %u "$path")" -g "$(stat -c %g "$path")" -m "$(stat -c %a "$path")" "new/$name" "$path"
  done
  echo "== prompt sizes after (warn above 56000, limit 60000)"
  if ! sizes; then
    echo "!! an instance no longer assembles - restoring the files" >&2
    for t in "${todo[@]}"; do
      IFS=: read -r path name <<<"$t"
      cp -a "$tmp/$name.before" "$path"
    done
    sizes || true
    exit 1
  fi
fi

note=/srv/farm/ws/inbox/meta/2026-11-14-phase11e-tools-roles.md
[[ -e $note ]] || install -o harness -g "$(stat -c %G /srv/farm/ws/inbox/meta)" -m 664 inbox-meta-2026-11-14-phase11e-tools-roles.md "$note"
echo "Installed phase 11e. Paste everything from '== check the installed files' down."
