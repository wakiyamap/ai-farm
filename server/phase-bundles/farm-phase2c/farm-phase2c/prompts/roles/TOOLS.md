# Tool catalog

One line per tool. Whoever adds a tool adds its line here. The commands below are placeholders: replace them with the real ones.

| Tool | What it does | How to call | Used by |
|---|---|---|---|
| RPC relay | All chain reads (JSON-RPC over HTTP). Chains: base, arbitrum, ethereum. Lanes: live > paper > research; each lane has a daily Alchemy budget, then public nodes. Read-only methods only; sending is the gate's job. `GET $RPC_RELAY_URL/health` shows today's spend | `curl -s -X POST "$RPC_RELAY_URL/<chain>?lane=<lane>" -H 'content-type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}'` | all |
| ledger | Pre-ingested events (liquidations and similar) on base/arbitrum/ethereum, refreshed every 15 min; `actor_daily` shows who is active. It is a head start, not the whole chain: anything else is one `eth_getLogs` away through the relay | `ledger top --chain base --days 7` / `ledger query "<SQL>"` / `ledger sources` | earner, paper-reviewer, researcher |
| ledger add-source | Track a new event in the ledger yourself (no approval needed, bounded CU). Write the JSON spec to `scratch/`, then install it | `ledger add-source scratch/<name>.json` | earner, researcher |
| simulate | eth_call / fork simulation of a transaction | `{{SIM_CMD}} <chain> <tx.json>` | earner, paper-reviewer |
| KB schema | Tables and columns of the knowledge base | `kb schema` | all |
| KB query | Read-only SQL; at most 50 rows, 10 s | `kb query "SELECT ... WHERE ... LIMIT 20"` | all |
| KB write | Validated insert / update; records author and run; rejects duplicates with the existing id | `kb add <table> '<json>'` / `kb update <table> <id> '<json>'` | all |
| wiki search | Ranked matches: path, type, updated, first line (max 20) | `wiki search "<terms>" --limit 10` | all |
| wiki read | Full page | `wiki read <path>` | all |
| wiki history | Recent commits for a page | `wiki history <path>` | all |
| wiki write | Write a page from a draft file and commit it | `wiki write <path> -m "<message>" --file scratch/<draft>.md` | all |
| bot search | Past bots: code, PnL, stop reason | `{{BOTS_CMD}} search "<query>"` | earner, meta |
| paper runner | Start / stop / logs / archive of a paper bot (runs it as a service) | `{{PAPER_CMD}} start\|stop\|logs <id>` / `{{PAPER_CMD}} archive <id> --reason "<reason>"` | earner, paper-reviewer (archive) |
| gate | Promote, fund, restart, status; stop = service stop + cancel pending tx + revoke approvals + sweep + archive | `gate promote\|fund\|restart\|status\|stop <id>` / `gate stop --all` | paper-reviewer (promote), live-operator |
| X feed | Received posts from followed accounts | `{{XFEED_CMD}} recent --since <time>` | earner, researcher |
| DefiLlama | Protocol, TVL and yield data | `{{LLAMA_CMD}} ...` | earner, researcher |
| web | Web search and fetch | harness built-in | all |
