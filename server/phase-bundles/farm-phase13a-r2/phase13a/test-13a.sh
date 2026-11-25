#!/usr/bin/env bash
# Offline test of the patched run-role: test-13a.sh <patched run-role>
# Pulls claude_tools() out of the file and calls it for each role.
set -euo pipefail
f="${1:?usage: test-13a.sh <run-role>}"
bash -n "$f"
fn="$(sed -n '/^claude_tools() {$/,/^}$/p' "$f")"
[[ -n "$fn" ]] || { echo "FAIL: claude_tools not found"; exit 1; }
eval "$fn"
fail=0
ok() { echo "  ok: $1"; }
bad() { echo "  FAIL: $1"; fail=1; }
has() { [[ ",$1," == *",$2,"* ]]; }

ROLE=earner; e="$(claude_tools)"
for want in 'Bash(paper start *)' 'Bash(python3 *)' 'Bash(forge *)' 'Edit(//srv/farm/ws/bots/paper/**)' \
            'Edit(//srv/farm/ws/claims/**)' 'Bash(rm /srv/farm/ws/claims/*)' 'Bash(kb *)' 'Bash(explorer *)'; do
  if has "$e" "$want"; then ok "earner has $want"; else bad "earner lacks $want"; fi
done
for deny in 'Bash(gate promote *)' 'Bash(gate *)' 'Bash(paper archive *)' 'Bash(paper *)' 'WebFetch' \
            'Edit(//srv/farm/prompts/roles/**)' 'Edit(//srv/farm/ws/**)'; do
  if has "$e" "$deny"; then bad "earner must not have $deny"; else ok "earner has no $deny"; fi
done
[[ "$e" != *$'\n'* ]] && ok "earner list is one line" || bad "earner list has a newline"

# the other roles are unchanged by this patch
ROLE=researcher; r="$(claude_tools)"
has "$r" 'WebFetch' && ! has "$r" 'Bash(paper start *)' && ok "researcher unchanged" || bad "researcher changed"
ROLE=paper-reviewer; p="$(claude_tools)"
has "$p" 'Bash(gate promote *)' && ! has "$p" 'Bash(python3 *)' && ok "paper-reviewer unchanged" || bad "paper-reviewer changed"
ROLE=nosuch; x="$(claude_tools)"
! has "$x" 'Bash(python3 *)' && has "$x" 'Bash(kb *)' && ok "unknown role gets the common list" || bad "fallback changed"
(( fail == 0 )) && echo "all tests passed" || { echo "TESTS FAILED"; exit 1; }
