#!/usr/bin/env bash
# Phase 10k offline test: runs a copy of assemble-prompt in a temp tree (paths rewritten, runuser
# replaced by a pass-through). Usage: test-10k.sh <assemble-prompt> [--old]
set -uo pipefail
src="${1:?usage: test-10k.sh <assemble-prompt> [--old]}"; old="${2:-}"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin" "$T/srv/farm/prompts/roles" "$T/srv/farm/runners" "$T/srv/farm/ws/inbox/meta" "$T/etc/farm"
printf '#!/bin/sh\nshift 3\nexec "$@"\n' > "$T/bin/runuser"      # runuser -u harness -- cmd...
printf '#!/bin/sh\nmkdir -p "$(eval echo \\${$#})"\n' > "$T/bin/install"   # only `install -d ... DIR` is used
chmod 755 "$T/bin/runuser" "$T/bin/install"
sed -e "s#/srv/farm#$T/srv/farm#g" -e "s#/etc/farm#$T/etc/farm#g" "$src" > "$T/assemble-prompt"
echo "earner-local earner dsh qwen" > "$T/etc/farm/roles.conf"
P="$T/srv/farm/prompts"; N="$T/srv/farm/ws/inbox/meta/prompt-size-earner-local.md"
fill() { head -c "$1" /dev/zero | tr '\0' 'x' > "$P/roles/TOOLS.md"; }      # total = $1 + 10004 + 4
head -c 5000 /dev/zero | tr '\0' 'c' > "$P/common.md"; head -c 5000 /dev/zero | tr '\0' 'r' > "$P/roles/earner.md"
run() { PATH="$T/bin:$PATH" bash "$T/assemble-prompt" earner-local >"$T/out" 2>&1; echo $?; }
fails=0
check() { if eval "$2"; then echo "  PASS  $1"; else echo "  FAIL  $1"; [ -s "$T/out" ] && sed 's/^/        /' "$T/out" | tail -n 3; fails=$((fails+1)); fi; }

echo "== ${old:+before 10k (installed file)}${old:-phase 10k}" | sed 's/--old//'
fill 40000; rc=$(run)
check "a 50 kB prompt is assembled, no note" '[ "$rc" = 0 ] && [ -s "$T/srv/farm/runners/earner-local/prompt.md" ] && [ ! -e "$N" ]'
fill 47000; rc=$(run)
check "a 57 kB prompt is assembled and a note for meta appears with the size" '[ "$rc" = 0 ] && grep -qx "size: 57004" "$N" 2>/dev/null && grep -q "close to its size limit" "$N"'
touch -d "2020-01-01" "$N" 2>/dev/null; rc=$(run)
check "the note is not rewritten while the size is unchanged" '[ "$rc" = 0 ] && [ "$(stat -c %Y "$N" 2>/dev/null)" = "$(date -d 2020-01-01 +%s)" ]'
fill 51000; rc=$(run)
check "a 61 kB prompt still fails (exit 1) and the note says the instance cannot start" '[ "$rc" = 1 ] && grep -q "cannot start" "$N" 2>/dev/null && grep -qx "size: 61004" "$N"'
fill 40000; rc=$(run)
check "back at 50 kB the note is removed" '[ "$rc" = 0 ] && [ ! -e "$N" ]'
chmod 555 "$T/srv/farm/ws/inbox/meta"; fill 47000; rc=$(run); chmod 755 "$T/srv/farm/ws/inbox/meta"
if [ "$(id -u)" = 0 ]; then echo "  (skipped as root: a note directory that cannot be written)"; else
check "a note that cannot be written does not stop the session" '[ "$rc" = 0 ]'; fi
if [ -z "$old" ]; then [ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }; fi
exit 0
