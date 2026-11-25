trial: old TEL -> new TEL (TelcoinV3) public migration arbitrage between two Uniswap v4 ETH pools on Base (cheap-chain trial, decision 2026-11-17).

## What it does

Telcoin replaced its token. `TokenMigration` `0x2703e00cae30a7707e4d18c38f8cb6a4a40c2703` (verified source,
`scratch/rec73/src-mig`) has a public `migrate()` (`0x8fd3ab80`, only `nonReentrant` and `whenNotPaused`): it escrows
the caller's whole balance of old TEL `0x09be1692ca16e06f536f0038ff11d1da8524adb1` (2 decimals) and mints the same
amount of TelcoinV3 `0x7e13b43065380acdec1c2d138c579cbbbafa0731` (18 decimals). No fee, not paused, open until
`migrationExpiry` 2027-09-24T19:08:39Z (read on chain 2026-11-22). Both tokens trade against native ETH on the
Uniswap v4 PoolManager `0x498581ff718922c3f8e6a244956af099b2652b2b`:

- old TEL pool: (ETH, old TEL, fee 3000, tick spacing 60, hooks `0x23ab2e6d4ab0c5f872567098671f1ffb46fd2500` =
  verified `TELxIncentiveHook`, an LP incentive tracker that does not change swaps);
- new TEL pool: (ETH, new TEL, fee 3000, tick spacing 60, no hooks).

The migration is one-way, so only "old TEL cheaper than new TEL by more than the two 0.3 pct fees" can be closed.
One transaction through the executor does, inside a single PoolManager `unlock` (v4 flash accounting: no principal,
no flash loan): ETH -> old TEL, `migrate()`, new TEL -> ETH, take the difference, pay the bot wallet. It reverts
unless the wallet is paid at least `minProfit` (= this send's cost cap).

Feed bot: it waits on the farm feed `/logs/base` for `Transfer(address,address,uint256)` (topic0 `0xddf252ad...b3ef`)
on the two TEL tokens (one filter; 18 + 557 logs in the 24 h to 2026-11-22T11:49Z; Base had 7 of 16 filters in use).
The PoolManager's `Swap` event is not subscribed (one emitter for every v4 pool on Base). On an event it does ONE
`eth_call` of the executor's `probe()` with 13 sizes (0.002-0.56 ETH), at most one look per 3 s; when the best gain
is above 1.3 x the send's cost cap it sends that size. It re-reads on `gap`, 429, 503 or a connection error, keeps a
300 s safety poll and looks again 4, 15 and 45 s after a look that saw a gain.

## Competition, last 7 days (Base blocks 57,762,844-60,786,844; `scratch/rec73/census.py`, `scratch/trial-tel-migrate-base/windows.py`, `windows.json`, `stats.py`)

- 40 `TokensMigrated` logs: 38 arbitrage transactions (the receipt also has v4 `Swap` logs) and 2 plain user
  migrations. Control in the same run: 598 `Transfer` logs of the new token in the last 504,000 blocks.
- Takers: executor `0x041b537387b319093b180a1c74239c9b8892ccdd` 36 takes from 30 rotating `0xc0ffee...` sender EOAs,
  profit paid to `0xc0ffeefeed8b9d271445cf5d1d24d74d2ca4235e` (the operator behind the farm's ICHI and pod copies;
  first take 2026-11-16T05:45:17Z, last 2026-11-20T19:26:35Z, block 60,062,099);
  `0x63d62548b665b240f520f80b38a4d2d3d89886d8` 1 take (sender `0x5c1547d8...`, block 59,995,242);
  `0xfdc4464f69fcfd0fc68f202a81ef4d3aeb398f54` 1 take (sender `0xb02ca8f1...`, block 60,000,937: the largest, 0.00526 ETH).
- Gross of the farm route at the parent block of each take: 0.012938 ETH in total (22.1 USD at 1,704.5 USD/ETH),
  median 0.000035 ETH, minimum 0.0000067, maximum 0.00526. Three takes above 0.001 ETH make 0.0088 ETH of it.
- Fee level: priority fee median 0.0044 gwei, range 0.001-0.61 gwei (the three large takes paid 0.13, 0.2 and
  0.61 gwei); tx index median 12, range 2-164; 180,139 gas median; cost median 1.9e12 wei (0.003 USD), L1 fee 2.3e9 wei.
- Blocks to take (the farm executor's `probe()` as a code override on the state N blocks before each take; a gain of
  0.00001 ETH or more still there):

  | before the take | takes of 38 | sum of those gains |
  |---|---|---|
  | 1 block (0.2 s) | 34 | 0.012909 ETH |
  | 5 blocks (1 s) | 26 | 0.007850 ETH |
  | 15 blocks (3 s) | 20 | 0.000922 ETH |
  | 50 blocks (10 s) | 9 | 0.000160 ETH |
  | 150 blocks (30 s) | 2 | 0.000021 ETH |
  | 300 blocks (60 s) | 1 | 0.000011 ETH |
  | 9,000 blocks (30 min) | 0 | 0 |

  The large gaps are taken within 1 s (out of reach at a 3 s reaction). The many small ones (0.00001-0.00015 ETH
  against a cost of about 0.000003 ETH) stand 3-10 s: about half of all takes. That half is what the trial measures.
- State at head 60,788,846 (2026-11-22T11:49:04Z): no gap (probe 0 at every size); the last take was 40 h earlier.

## Loss bound

A lost send costs gas only: about 290,000 gas (limit 1.2 x the estimate) at <= 0.2 gwei, under 0.95 USD at 4,000 USD
per ETH (in practice about 0.003-0.03 USD). Base charges the L1 data fee at inclusion, so the hard worst case of a
send is the wallet's native balance: capital 0.75 USD, all native, no principal, and the live branch refuses to send
while the wallet is worth 0.95 USD or more (a win above about 0.2 USD therefore needs a sweep before the next send;
the log row is `opportunity_skip wallet_at_or_above_usd_bound`).

## Read cost

Per look: 1 `eth_call` (26 CU). Looks: feed events at most one per 3 s (575 Transfer logs a day measured, many in the
same transaction: about 300 looks) + 288 safety polls + follow-ups = about 650 looks a day = 17,000 CU. An open gap
adds 1 `eth_getBlockByNumber`, 1 `eth_estimateGas`, 1 `eth_call` and (live) 1 `eth_getBalance`, 1 `eth_call`,
receipt polls and 1 `eth_getLogs`: under 400 CU each. About 20,000 relay CU a day = 0.011 USD at 0.53 USD per million
CU; code cap 95,000 CU a day (then it sleeps to 00:00 UTC). Feed CU for about 575 logs a day is metered by the feed.

## Files

- `bot.py` (self-contained; live branch uses `/opt/farm/lib/farmbot_signer.py`, executor from `EXECUTOR_ADDR_BASE` /
  `EXECUTOR_ADDR`), `run.sh`, `executor-runtime.hex` (paper code override = `eth_getCode` of the fork deployment).
- Executor source `scratch/trial-tel-migrate-base/contracts/src/V4MigrateArb.sol`; proof `scratch/trial-tel-migrate-base/proof.py`;
  self-test `selftest.py` (the bot's own `check()` on the state of blocks 58,734,313 and 60,062,098: `opportunity` +
  `paper_sim success`; on 60,788,846: nothing).
- Logs `logs/bot.jsonl`: `start`, `feed`, `look`, `opportunity`, `opportunity_skip`, `simulate_revert`, `paper_sim`,
  `send_result` (won / lost, gas used, winner's block), `feed_error`, `feed_gap`, `read_budget`, `loop_error`.

## Not covered

Polygon has the same migrator (old TEL `0xdf7837de...`) and far deeper pools, but old TEL trades 0.6 pct above new
TEL there and no arbitrage contract has ever migrated (5,706 migrations checked): nothing to take (KB leads:403).
