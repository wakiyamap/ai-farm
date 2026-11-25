#!/usr/bin/env bash
# Phase 11c (2026-11-14): live bots never received EXECUTOR_ADDR. The role files and the gate's
# 10e check name that variable, but bot@.service only set BOT_MODE, BOT_ID, RPC_* and SIGNER_SOCK,
# so a bot written as `process.env.EXECUTOR_ADDR || '<fork address>'` ran live with the fork
# address and could not send (morpho-nextblock-ethereum; gearbox-v3-watcher-ethereum has the same
# line).
#  - /opt/farm/bin/bot-run: exports EXECUTOR_ADDR / EXECUTOR_ADDR_<CHAIN> from
#    state/executor.json, then execs the bot's run.sh
#  - drop-in bot@.service.d/executor-env.conf: ExecStart goes through bot-run
#  - every running live bot that has state/executor.json is restarted once (gate restart) and its
#    environment is checked. If one does not come back, the drop-in is removed and the bots are
#    restarted the old way.
# No contract is deployed and no funds move. Safe to re-run.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin S=/etc/systemd/system LIVE=/srv/farm/ws/bots/live
export PYTHONDONTWRITEBYTECODE=1
pyc() { python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$1"; }

for f in bot-run test-11c.py; do pyc "$f"; done
echo "== offline tests"
python3 -I -B test-11c.py bot-run

bot_env() {   # EXECUTOR_ADDR in the environment of the running bot, or "-"
  local pid; pid=$(systemctl show -p MainPID --value "bot@$1.service")
  [[ "$pid" =~ ^[1-9][0-9]*$ ]] || { echo "-"; return; }
  { tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null || true; } | sed -n 's/^EXECUTOR_ADDR=//p' | head -n 1 | grep . || echo "-"
}
recorded() {  # the addresses in state/executor.json, space separated
  python3 -I -B -c 'import json,sys; print(" ".join(sorted({v["address"] for v in json.load(open(sys.argv[1])).values()})))' "$LIVE/$1/state/executor.json" 2>/dev/null || echo "?"
}

echo "== live bots before"
todo=()
for d in "$LIVE"/*/; do
  [[ -d "$d" ]] || continue
  id=$(basename "$d")
  if [[ -e "$d/state/executor.json" ]]; then
    echo "  $id: recorded $(recorded "$id") | process has $(bot_env "$id") | $(systemctl is-active "bot@$id.service" || true)"
    if systemctl is-active --quiet "bot@$id.service"; then todo+=("$id"); fi
  else
    echo "  $id: no state/executor.json (not restarted)"
  fi
done

echo "== install bot-run and the drop-in"
install -o root -g root -m 755 bot-run "$B/bot-run"
install -d -m 755 "$S/bot@.service.d"
install -o root -g root -m 644 units/bot-executor-env.conf "$S/bot@.service.d/executor-env.conf"
systemctl daemon-reload
systemctl cat bot@.service | { grep -c '^ExecStart=/opt/farm/bin/bot-run ' || true; } | sed 's/^/  ExecStart through bot-run: /'

rollback() {
  echo "!! $1 - removing the drop-in and restarting the bots the old way" >&2
  rm -f "$S/bot@.service.d/executor-env.conf"
  rmdir "$S/bot@.service.d" 2>/dev/null || true
  systemctl daemon-reload
  for id in "${todo[@]}"; do
    systemctl reset-failed "bot@$id.service" 2>/dev/null || true
    systemctl restart "bot@$id.service" || true
  done
  sleep 10
  for id in "${todo[@]}"; do echo "  $id: $(systemctl is-active "bot@$id.service" || true)"; done
  exit 1
}

if (( ${#todo[@]} )); then
  echo "== restart the live bots that have an executor"
  since=$(date -u '+%Y-%m-%d %H:%M:%S')
  for id in "${todo[@]}"; do
    runuser -u harness -- "$B/gate" restart "$id" 2>&1 | sed 's/^/  /' || true
  done
  sleep 20
  bad=0
  for id in "${todo[@]}"; do
    state=$(systemctl is-active "bot@$id.service" || true)
    have=$(bot_env "$id"); want=$(recorded "$id")
    if [[ "$state" == active && "${have,,}" == "${want,,}" ]]; then
      echo "  OK   $id: active, EXECUTOR_ADDR=$have"
    elif [[ "$state" == active && "$want" == *" "* ]]; then
      echo "  OK   $id: active, addresses differ per chain ($want); see EXECUTOR_ADDR_<CHAIN>"
    else
      echo "  BAD  $id: $state, process has $have, recorded $want"
      bad=1
    fi
    journalctl -u "bot@$id.service" --since "$since" --no-pager -o cat | tail -n 6 | sed 's/^/       | /'
  done
  (( bad == 0 )) || rollback "a bot did not come back with its executor address"
else
  echo "== no running live bot has an executor; nothing restarted"
fi

note=/srv/farm/ws/inbox/meta/2026-11-14-phase11c-executor-env.md
[[ -e $note ]] || install -o harness -g "$(stat -c %G /srv/farm/ws/inbox/meta)" -m 664 inbox-meta-2026-11-14-phase11c-executor-env.md "$note"
echo "Installed phase 11c. Paste everything from '== offline tests' down."
