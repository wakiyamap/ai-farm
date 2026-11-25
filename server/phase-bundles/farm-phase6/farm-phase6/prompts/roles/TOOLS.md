# Tool catalog

One line per tool. Whoever adds a tool adds its line here. The commands below are placeholders: replace them with the real ones.

| Tool | What it does | How to call | Used by |
|---|---|---|---|
| RPC relay | All chain reads (JSON-RPC over HTTP). Chains: base, arbitrum, ethereum. Lanes: live > paper > research; each lane has a daily Alchemy budget, then public nodes. Read-only methods only (incl. `debug_traceTransaction`, `debug_traceCall`, `trace_block`, `alchemy_getAssetTransfers`; these go to Alchemy and cost 40-1000 CU each); sending is the gate's job. `GET $RPC_RELAY_URL/health` shows today's spend | `curl -s -X POST "$RPC_RELAY_URL/<chain>?lane=<lane>" -H 'content-type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}'` | all |
| ledger | Pre-ingested events (liquidations and similar) on base/arbitrum/ethereum, refreshed every 15 min; `actor_daily` shows who is active. It is a head start, not the whole chain: anything else is one `eth_getLogs` away through the relay | `ledger top --chain base --days 7` / `ledger query "<SQL>"` / `ledger sources` | earner, paper-reviewer, researcher |
| ledger add-source | Track a new event in the ledger yourself (no approval needed, bounded CU). Write the JSON spec to `scratch/`, then install it | `ledger add-source scratch/<name>.json` | earner, researcher |
| simulate | Dry-run a transaction: `eth_call` (revert / return) or `debug_traceCall` (full trace) through the relay, against `latest`. No local fork yet; propose one via the researcher if a strategy needs state changes across several calls | `curl ... -d '{"method":"eth_call","params":[{"from":"0x..","to":"0x..","data":"0x.."},"latest"]}'` | earner, paper-reviewer |
| KB schema | Tables and columns of the knowledge base | `kb schema` | all |
| KB query | Read-only SQL; at most 50 rows, 10 s | `kb query "SELECT ... WHERE ... LIMIT 20"` | all |
| KB write | Validated insert / update; records author and run; rejects duplicates with the existing id | `kb add <table> '<json>'` / `kb update <table> <id> '<json>'` | all |
| wiki search | Ranked matches: path, type, updated, first line (max 20) | `wiki search "<terms>" --limit 10` | all |
| wiki read | Full page | `wiki read <path>` | all |
| wiki history | Recent commits for a page | `wiki history <path>` | all |
| wiki write | Write a page from a draft file and commit it | `wiki write <path> -m "<message>" --file scratch/<draft>.md` | all |
| bot archive | Stopped bots with their code, manifest and `ARCHIVE.md` (reason). Search with grep | `grep -ril "<term>" bots/archive/*/manifest.yaml` then read the directory | earner, meta |
| signer (from inside a live bot only) | Unix socket `$SIGNER_SOCK`: `{"op":"send",...}` → signed + broadcast after policy; `{"op":"limits"}` shows what is allowed today | `/opt/farm/lib/farmbot_signer.py` | live bots |
| fork | Local anvil fork of each mainnet (base 9001, arbitrum 9002, ethereum 9003), forked from the relay's research lane. Fake funds, impersonation, deploys, replays. Shared: `fork reset` before clean measurements | `fork status` / `fork reset <chain> [block]` / `fork fund <chain> <addr> <eth>` / `fork deploy <chain> <bytecode.hex>` / `fork send <chain> '<tx json>'` / `fork replay <chain> <txhash>` / `fork trace <chain> <txhash>` | earner, paper-reviewer, researcher |
| forge | Solidity compiler and test runner (Foundry) for executor contracts. Work in `scratch/<bot>/contracts`; `forge test --fork-url $(fork url base)` runs tests against the fork | `/opt/foundry/bin/forge build` / `forge test` / `cast` for ABI encoding | earner, paper-reviewer |
| paper runner | Run a bot in `bots/paper/<id>/` as a supervised service (user farmbot, paper lane, no keys). `paper list` / `paper status <id>` / `paper logs <id>` (stdout/stderr only; a bot's own files are under `bots/paper/<id>/logs/`) | `paper start <id>` / `paper stop <id>` / `paper restart <id>` / `paper archive <id> --reason "<why>"` | earner, paper-reviewer (archive), live-operator |
| gate | Deploy gate (holds keys; enforces X=2000, n=200/day, L=20, cap 400/bot). `status` shows capital, today's loss, frozen flag, every live bot's address/balances/nonces | `gate status [id]` / `gate promote <id>` / `gate fund <id> <usd>` / `gate restart <id>` / `gate stop <id>` / `gate stop --all` | paper-reviewer (promote), live-operator (all), earner/meta (status) |
| X feed | Not available yet. If posts from specific accounts would help, the researcher proposes a feed (cost, accounts) in `inbox/human/` | — | researcher |
| DefiLlama | Public API, no key: protocols, TVL, yields. Filter with `jq`; responses are large | `curl -s https://api.llama.fi/protocols \| jq '[.[] \| select(.chains[]? == "Base")] \| length'` / `curl -s https://yields.llama.fi/pools` | earner, researcher |
| web | Web search and fetch | harness built-in | all |
