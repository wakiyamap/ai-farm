#!/usr/bin/env bash
# Offline tests for phase 16e: test-16e.sh <context-paper-reviewer> <scout.conf>
set -euo pipefail
wrap="${1:?context-paper-reviewer}"; conf="${2:?scout.conf}"
fail=0; ok() { echo "  ok: $1"; }; bad() { echo "  FAIL: $1"; fail=1; }
bash -n "$wrap"
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
cat > "$t/base" <<'B'
#!/usr/bin/env bash
echo "### Review queue"
echo "| bot | service | expedite | last decision | next_review_at | changed since review | due |"
for b in a-claude-bot b-codex-bot; do echo "| $b | running | false | none |  | - | NEW |"; done
echo "Slots: 2 running / 12"
B
chmod +x "$t/base"
out=$(FARM_CTX_BASE="$t/base" bash "$wrap" paper-reviewer)
grep -q '^| b-codex-bot | .* | NEW |$' <<<"$out" && ok "codex-built bot is due for paper-reviewer" || bad "codex-built bot not due"
grep -q 'other-reviewer |' <<<"$out" && bad "an other-reviewer row remains" || ok "no other-reviewer rows"
grep -q '^Slots: 2' <<<"$out" && grep -q 'only paper reviewer' <<<"$out" && ok "base lines kept, note added" || bad "lines lost"
grep -qE '^(User|Group)=' "$conf" && bad "scout.conf sets a user" || ok "scout.conf runs as the default user"
grep -v '^#' "$conf" | grep -q 'qwen\|8003\|\.dsh' && bad "scout.conf still refers to Qwen/dsh" || ok "no Qwen/dsh in scout.conf"
grep -qx 'RuntimeMaxSec=35min' "$conf" && grep -qx 'Environment=SESSION_MAX_MIN=35' "$conf" && ok "35-minute cut-off kept" || bad "cut-off"
mkdir -p "$t/q"; c=$(sed -n 's/^ExecCondition=\/bin\/sh -c //p' "$conf" | tr -d "'" | sed "s#/srv/farm/ws/scout/queue#$t/q#")
sh -c "$c" && bad "condition passes on an empty queue" || ok "condition fails on an empty queue"
touch "$t/q/1-00001-x.json"; sh -c "$c" && ok "condition passes with a candidate" || bad "condition fails with a candidate"
(( fail == 0 )) && echo "all tests passed" || { echo "TESTS FAILED"; exit 1; }
