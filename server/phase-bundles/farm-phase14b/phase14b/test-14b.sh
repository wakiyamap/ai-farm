#!/usr/bin/env bash
# Offline tests for phase 14b: test-14b.sh <scout-enum> <context-scout> <scout-done>
set -euo pipefail
enum=$(realpath "$1"); ctx=$(realpath "$2"); done_=$(realpath "$3")
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
fail=0; ok() { echo "  ok: $1"; }; bad() { echo "  FAIL: $1"; fail=1; }
cat > "$t/kb" <<'K'
#!/usr/bin/env python3
import json, re, sys
sql = sys.argv[-1]
if "id > 0" not in sql: sys.exit(0)          # one page only
if "FROM leads" in sql:
    print(json.dumps({"id": 7, "chain": "optimism", "target": "hai oraclejob race"}))
elif "FROM actors" in sql:
    print(json.dumps({"id": 1, "chain": "base", "address": "0x1111111111111111111111111111111111111111"}))
elif "FROM protocols" in sql:
    print(json.dumps({"id": 1, "chain": "base", "protocol": "known_proto"}))
K
cat > "$t/ledger" <<'L'
#!/usr/bin/env bash
[[ $3 == base ]] && printf 'actor 0x1111111111111111111111111111111111111111 40\nactor 0x2222222222222222222222222222222222222222 12\n'
exit 0
L
cat > "$t/llama.json" <<'J'
[{"slug":"known-proto","name":"Known Proto","category":"Dexs","chainTvls":{"Base":500000},"listedAt":1700000000},
 {"slug":"new-thing","name":"New Thing","category":"Yield","chainTvls":{"Base":250000,"Ethereum":900000,"Solana":1e9},"listedAt":1790000000},
 {"slug":"tiny","name":"Tiny","category":"Dexs","chainTvls":{"Arbitrum":5000}},
 {"slug":"an-exchange","name":"An Exchange","category":"CEX","chainTvls":{"Base":9e9}}]
J
chmod +x "$t/kb" "$t/ledger"
export SCOUT_WS="$t/ws" KB_BIN="$t/kb" LEDGER_BIN="$t/ledger" LLAMA_FILE="$t/llama.json"
mkdir -p "$t/ws"
python3 -I "$enum" > "$t/out1" 2>&1 || { cat "$t/out1"; bad "enum run 1"; }
ls "$t/ws/scout/queue" > "$t/q1"
[[ $(wc -l < "$t/q1") == 4 ]] && ok "4 candidates queued (trial, actor, 2 protocol)" || { cat "$t/q1"; bad "queue count"; }
head -1 "$t/q1" | grep -q '^1-00000-trial-optimism-lead7' && ok "trial first" || bad "order: trial not first"
sed -n 2p "$t/q1" | grep -q '^2-00000-actor-base-0x2222' && ok "unknown actor second, known actor skipped" || bad "actor"
grep -q '^3-.*protocol-base-new-thing' "$t/q1" && grep -q '^4-.*protocol-ethereum-new-thing' "$t/q1" && ok "cheap chain before ethereum" || bad "protocol tiers"
! grep -qE 'known-proto|tiny|exchange|solana' "$t/q1" && ok "known, small, CEX and non-farm chains skipped" || bad "filters"
python3 -I "$enum" > /dev/null 2>&1
[[ $(ls "$t/ws/scout/queue" | wc -l) == 4 ]] && ok "second run adds no duplicates" || bad "duplicates"
c1=$(FARM_RUN_ID=r1 python3 -I "$ctx"); c2=$(FARM_RUN_ID=r2 python3 -I "$ctx")
id1=$(sed -n 's/^- candidate id: //p' <<<"$c1"); id2=$(sed -n 's/^- candidate id: //p' <<<"$c2")
[[ $id1 == trial-optimism-lead7 && -n $id2 && $id1 != "$id2" ]] && ok "two sessions take two different candidates" || bad "take: $id1 / $id2"
grep -q 'kb-file.py update leads 7' <<<"$c1" && ok "trial steps filled in" || bad "trial steps"
grep -q '"run_id": "r1"' "$t/ws/scout/doing/$id1.json" && ok "doing file carries the run_id" || bad "run_id"
FARM_RUN_ID=r1 python3 -I "$done_" "$id1" --verdict pays_strangers --line "x" --kb attempts:1 > /dev/null
[[ -f $t/ws/scout/done/$id1.json && ! -f $t/ws/scout/doing/$id1.json ]] && ok "scout-done moves doing -> done" || bad "done"
python3 -I "$done_" "$id1" --verdict unclear --line x > /dev/null 2>&1 && bad "closing twice should fail" || ok "closing twice is refused"
python3 -I "$done_" "$id2" --verdict maybe --line x > /dev/null 2>&1 && bad "bad verdict accepted" || ok "unknown verdict refused"
touch -d '2 hours ago' "$t/ws/scout/doing/$id2.json"
python3 -I "$enum" > /dev/null 2>&1
ls "$t/ws/scout/queue" | grep -q "$id2" && ok "stale doing file returns to the queue" || bad "requeue"
python3 -I "$enum" > /dev/null 2>&1
grep -q '"retries": 1' "$t/ws/scout/queue/"*"$id2.json" && ok "retry counted" || bad "retries"
rm -f "$t/ws/scout/queue/"*; e=$(FARM_RUN_ID=r3 python3 -I "$ctx")
grep -q 'candidate: none' <<<"$e" && ok "empty queue says no_candidate" || bad "empty"
(( fail == 0 )) && echo "all tests passed" || { echo "TESTS FAILED"; exit 1; }
