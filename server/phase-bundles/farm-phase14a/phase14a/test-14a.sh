#!/usr/bin/env bash
# Offline tests for phase 14a: test-14a.sh <patched run-role> <context-paper-reviewer>
set -euo pipefail
rr="${1:?run-role}"; wrap="${2:?context-paper-reviewer}"
fail=0
ok() { echo "  ok: $1"; }
bad() { echo "  FAIL: $1"; fail=1; }
bash -n "$rr"; bash -n "$wrap"

# 1. run-role: builder gets exactly the earner tool list; other roles unchanged
fn="$(sed -n '/^claude_tools() {$/,/^}$/p' "$rr")"; eval "$fn"
ROLE=earner; e="$(claude_tools)"; ROLE=builder; b="$(claude_tools)"
[[ "$e" == "$b" && "$b" == *'Bash(paper start *)'* ]] && ok "builder has the earner list" || bad "builder list differs"
[[ ",$b," != *',Bash(gate promote *),'* && ",$b," != *',Bash(paper archive *),'* ]] && ok "builder cannot promote or archive" || bad "builder can promote/archive"
ROLE=paper-reviewer; p="$(claude_tools)"
[[ "$p" == *'Bash(gate promote *)'* ]] && ok "paper-reviewer list unchanged" || bad "paper-reviewer changed"

# 2. reviewer routing with a fake workspace and base generator
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
mkdir -p "$t/ws/bots/paper/"{a-claude-bot,b-codex-bot,c-qwen-bot,d-no-author}
printf 'author: builder/claude-mythos-5-2\n' > "$t/ws/bots/paper/a-claude-bot/manifest.yaml"
printf 'author: builder/gpt-6-sol\n' > "$t/ws/bots/paper/b-codex-bot/manifest.yaml"
printf 'author: earner/qwen3.8-flash-next\n' > "$t/ws/bots/paper/c-qwen-bot/manifest.yaml"
cat > "$t/base" <<'B'
#!/usr/bin/env bash
echo "### Review queue"
echo "| bot | service | expedite | last decision | next_review_at | changed since review | due |"
for b in a-claude-bot b-codex-bot c-qwen-bot d-no-author; do echo "| $b | running | false | none |  | - | NEW |"; done
echo "Slots: 4 running / 12"
B
chmod +x "$t/base"
run() { FARM_CTX_WS="$t/ws" FARM_CTX_BASE="$t/base" bash "$wrap" "$1"; }
cx=$(run paper-reviewer); cl=$(run paper-reviewer-claude)
due() { grep -E "^\| $2 \|" <<<"$1" | awk -F'|' '{gsub(/ /,"",$(NF-1)); print $(NF-1)}'; }
[[ $(due "$cx" a-claude-bot) == NEW && $(due "$cl" a-claude-bot) == other-reviewer ]] && ok "claude-built -> codex reviewer" || bad "claude-built routing"
[[ $(due "$cx" b-codex-bot) == other-reviewer && $(due "$cl" b-codex-bot) == NEW ]] && ok "codex-built -> claude reviewer" || bad "codex-built routing"
[[ $(due "$cx" c-qwen-bot) == NEW && $(due "$cl" c-qwen-bot) == other-reviewer ]] && ok "qwen-built -> codex reviewer" || bad "qwen-built routing"
[[ $(due "$cx" d-no-author) == NEW && $(due "$cl" d-no-author) == other-reviewer ]] && ok "no author -> codex reviewer" || bad "no-author routing"
grep -q '^| bot | service' <<<"$cx" && grep -q '^Slots: 4' <<<"$cx" && ok "header and other lines kept" || bad "lines lost"
grep -c '| ' <<<"$cl" >/dev/null && [[ $(grep -c 'other-reviewer |' <<<"$cl") == 3 ]] && ok "claude reviewer sees 3 rows as other-reviewer" || bad "row count"
(( fail == 0 )) && echo "all tests passed" || { echo "TESTS FAILED"; exit 1; }
