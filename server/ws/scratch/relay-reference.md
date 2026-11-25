---
type: infra
chains: [base, arbitrum, ethereum, bsc, polygon, avalanche, optimism, hyperevm, elysium]
protocols: []
---
# RPC relay, fork, ledger and gate: full reference (moved out of TOOLS.md)

**Conclusion.** TOOLS.md keeps one short line per tool; the measured details, per-chain caps and dated incident history live here (moved verbatim by meta d14035aa on 2026-11-11, because the earner's assembled prompt went over the 60000-byte limit). For eth_getLogs parameter mistakes also read `pitfalls/relay-getlogs-invalid-params.md`.

## Relay: per-chain notes

- **elysium** (since 2026-11-11, chain 99901, Nitro, 100-200 ms blocks): `debug_*`/`trace_*` refused (401, run 8fbcce67); `eth_getLogs` ≤10000 blocks per request (run ecd4a38d); "hex string of odd length" = your value's digit count is odd (a 65-digit topic, meta 35f952d9); USDC `0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65`.
- **bsc..hyperevm** (since 2026-11-10): no `trace_*` on polygon/hyperevm.
- **bsc**: the public node serves no `eth_getLogs`, so bsc log scans cost Alchemy CU. Provider caps (run 0ff127bd, 11-10): ranges >5000 blocks rejected (`-32602 exceed maximum block range 5000`); topic-only Transfer/Approval over 5000 blocks exceed the response cap (≤1000 blocks worked: 36105 logs), so a bsc topic-only zero counts only with a ≤1000-block control that returns logs. At head, Transfer is ~305 logs/block: keep topic-only pages ≤125 blocks (`infra/bsc-head-density.md`).
- **bsc/polygon empty answers**: bsc topic-filtered `eth_getLogs` returned `[]` 11-10 13:20-13:31Z (inbox/meta/2026-11-10-bsc-getlogs-topics-empty.md) but matched at 14:1xZ (meta 5acefe05: relay-probe range 20=20, topic-only 234 with busiest emitter 58=58, the reported CAKE 500-block shape 103 logs; polygon/avalanche/optimism/hyperevm also equal): a bsc topic-filtered zero from before 14:00Z 11-10 is vacuous. It recurred 11-11 06:1xZ (run 77d73b72), and polygon answered topic-only and below-head `[]` 06:5x-07:0xZ (runs ee6ebe0b, 19a3e1cf; a public node then reported a head 31k blocks ahead); both matched again at 08:2xZ (meta 35f952d9: polygon topic-only 965, top emitter 617=617, range 66=66; bsc 145, 51=51, range 30=30). Human checked polygon heads 10:12Z 11-11: in step, no per-request relay log. **Rule: on bsc/polygon a zero counts only with a same-run, same-shape, same-window control that returns logs**; if it recurs, run `relay-probe.py ... --chain <chain>` in the same minute and report time + both head values.
- **arbitrum**: topic-only (no address) works up to 30000 blocks.
- **ethereum**: topic-only works since relay phase 6y (2026-11-09: public-node "specify an address"/-32602/empty answers are retried on Alchemy, not cached; meta b1462fd8: 512 logs in one block, address-filtered cross-check equal). Ethereum topic-only zeros from before 6y (e.g. 11-08 evening, attempts 600/603) are vacuous. `eth_getTransactionReceipt` / `eth_getBlockReceipts` return `result: null` for older txs (3 reports 11-06..11-08, with human): null is not "tx missing"; read the tx's logs with `eth_getLogs` on its block number and match `transactionHash`, or `debug_traceTransaction` callTracer. When a lane's Alchemy budget is spent (`/health`), `eth_getLogs` falls to a public node that rejects ranges >10000 blocks and answers only ~12k blocks back from head, surfaced as `all providers failed` (run f194c191, 11-09): that is budget, not a missing event.
- **base**: topic-only answered after 6y (42 logs, USDC 13 = 13 filtered, same run). Before 6y Base public nodes rejected it, and they intermittently reject multi-address arrays with `-32602 ... untagged enum Variadic` (retry with one address per request; `relay-log-scan.py` splits these automatically since run 4b7b514b, 2026-11-09; first seen run 95a7bdc8, 2026-11-07).
- **optimism**: dense (1078 Transfer logs / 10 blocks topic-only at head, run 57a18a2e): tiny windows only.

## Relay: methods and errors (all chains)

- Lanes: live > paper > research; each lane has a daily Alchemy budget, then public nodes. `GET $RPC_RELAY_URL/health` shows today's spend.
- Read-only methods only, incl. `debug_traceTransaction`, `debug_traceCall`, `trace_block`, `alchemy_getAssetTransfers` (Alchemy, 40-1000 CU each). State diffs need `{"tracer":"prestateTracer","tracerConfig":{"diffMode":true}}` (`callTracer` ignores `diffMode`); if that returns no `pre`/`post`, use pre/post balances on the fork.
- Calldata: `eth_getTransactionByHash` → `input` (20 CU; `eth_getTransaction` does not exist).
- `eth_getLogs`: address arrays work, at most 32 per call (split larger sets). `-32700 parse error` = your JSON body is malformed (build it with `json.dumps`). Never pad `topics` with more `null` slots than the event has topics (`[t0,null,null,null]` on 3-topic Transfer returns a silent `[]`, measured 2026-11-07). >10000 matching logs → -32000 or `alchemy: HTTP 400 Log response size exceeded` (run 7d1846d7, 260k-block bEIGEN scan): shrink the range (≤10k blocks for busy tokens).
- `latest`/`pending`/omitted-block reads were cached stale (ethereum 17-25 blocks) until relay phase 6w (2026-11-07, now cached ≤1 s); reading `eth_blockNumber` then the block by explicit number stays safe.
- `alchemy_getAssetTransfers` (human-verified, ethereum): `[{"fromBlock":"0x..","toBlock":"0x..","toAddress":"0x<checksummed>","category":["external"],"maxCount":"0x1"}]`. HTTP 400 = your params (hex-string `maxCount`, valid `category`, single checksummed address); since phase 6x the error carries Alchemy's reason. Valid categories: `external`, `internal`, `erc20`, `erc721`, `erc1155`, `specialnft` (`token` is not one: run 8d00ccae got `all providers failed: public: ... method is not available` with `["external","token"]`).
- `-32602 ... odd number of digits` / "hex string of odd length" = your address/hex/topic has a digit missing or extra (run 7bd92868's "relay bug" was a 39-digit address; count addresses to 40, topics to 64).
- Blockscout v2 address `/transactions` and `/logs` listings are intermittently empty for active contracts (run 8d00ccae): never conclude "0 txs" from them without a relay `eth_getLogs` cross-check.

## Fork details

- elysium (9009): `fork trace`/`replay` may be weaker (no Alchemy trace). Since phase 10j (11-11) `fork reset/replay elysium` sends `evm_mine` itself, so the fork stands at `<block>+1` and a replay runs one block later than mainnet (same state, block number/timestamp +1). A freshly booted fork service may show `Excess blob gas not set.` until the first `fork reset elysium`. The old `fork fund-token ... 1` workaround is no longer needed.
- hyperevm: keep every tx incl. the executor deploy under 2,000,000 gas (gate/signer refuse more).
- Old-block resets/state reads try Alchemy first (head−800+).
- Anvil limits (runs bc26fa71, a8e2e15e, 11-09): only callTracer works (no `debug_storageRangeAt`, `withStorage` is a no-op, `js` tracer broken, default structLogs empty); each untouched slot read is a relay fetch, so `eth_getStorageAt` scans ≤400 slots per request; inner custom-error data shows only in callTracer frames.
- `fork fund-token`: since phase 9h a failed impersonated transfer prints `FAILED ...` and exits 2: pick another holder after checking `balanceOf(holder)`. `fork deploy` status 0 at ~intrinsic gas = missing `--args`.
- Concurrency: `pitfalls/shared-fork-concurrency.md`.

## Ledger add-source details

- Since phase 9d (`decisions/human/2026-11-09-ledger-dynamic-events.md`) `event` is the full canonical signature incl. dynamic/tuple/array types (topic0 = its keccak); `indexed` names the leading indexed params (max 3; dynamic indexed = raw topic hash); `data` may name only the static one-word params at the front of the non-indexed ones (the first dynamic/tuple/array one ends the list, so `data: []` if it comes first). Interleaved indexed/non-indexed events: `actor_field: tx_from`, name nothing in `indexed`. `chains.<chain>` capped at 20 addresses.
- Phase 10h (11-11): emitters at the same block share one `eth_getLogs` (60 CU per chain and tick), a lagging emitter backfills first, `tx_from` sources no longer skip events when the budget runs out mid-range (gaps before 10h are not recovered; ask the human to rewind if a claim depends on one). 7-day catch-up ≈ hours on ethereum, most of a day on arbitrum, longer on elysium. Since 9e every agent source gets ≥600 CU per tick.
- Zero events count only once `tools/ledger-source-coverage.py` shows the cursor at the head.

## Gate details

- Phase 10f: an unreadable executor artifact is refused before the move/funding; a paper-dir artifact path is read from `bots/live/<id>/` after the move; a foreign `state/executor.json` is removed.
- Phase 10e: `stop`/`sweep` exit 3 "the sweep is incomplete" = service stopped, funds not all back, bot stays in `bots/live/` and counts toward X: rerun later, never report it as swept. `fund` refuses a top-up past 400 USD in the wallet. Executor bots must read `EXECUTOR_ADDR`/`state/executor.json` or `promote` refuses.
- Elysium (phase 10g): gas HYPE priced by HyperEVM's feed, so no elysium signing while HyperEVM is unreadable.

## Other tool history

- KB write: `/opt/farm/bin/kb` reads argv with no length limit; a parse error near the end (`Expecting ',' delimiter` at a column equal to your text's length) means the closing `}` never reached kb (shell cut it): use `tools/kb-file.py` (meta 3064be87). The 6 legacy hyphen protocol names were renamed in phase 6x.
- paper runner: since phase 6y an `ok` from `start`/`restart` means it is running.
- web: earner `web_search` registration fixed in phase 8a (2026-11-07 12:22Z).
- relay-log-scan `--chain` tests: bsc CAKE Transfer 500 blocks 103 logs, 1 request (meta 5acefe05); elysium USDC Transfer 4462000-4465800 950 logs, 2 requests (meta 718540da).
- relay-probe: ethereum USDC control address was wrong until meta b07502ea (11-09); elysium topic-only 3 logs, USDC 1=1, busiest 2=2 (meta 718540da); its 8-block range is ~1 s of chain, so 0=0 is normal there.
- manifest-check: meta 421c68f0 flagged 2 archived bots that read `EXEC_ADDRESS`; an inline `# comment` on `capital_usd` crashed a promote 11-10 (`principal_usdc` tolerates one).
