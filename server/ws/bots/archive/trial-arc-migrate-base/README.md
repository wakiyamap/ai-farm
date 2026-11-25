trial: old ARC -> new ARC public migration arbitrage on Base (cheap-chain trial, decision 2026-11-17).

## What it does

The ARC project replaced its token. The migrator `0xa1bc813c3323335407ee2c2330f6a0f3b7437cdb` (proxy, implementation
`0x7c2ef34d...` unverified) has a public `migrate(uint256)` (`0x454b0608`): it burns old ARC `0x5a4342f4...` and pays
new ARC `0x431151f2...` at 40 old : 1 new, at most 100,000 old per call. Old ARC still trades in a Uniswap V2 pair
against VIRTUAL (`0xb68f6d54...`), new ARC in a V2 pair against WETH (`0x2814a97e...`, 1.86 WETH deep). When old ARC
is cheap, one transaction through the executor does:

Morpho flash loan of WETH -> VIRTUAL (V2 `0xe31c372a...`) -> old ARC -> `migrate` in chunks -> new ARC -> WETH ->
repay -> unwrap the rest to the bot wallet. It reverts unless the wallet is paid at least `minProfit`
(= this send's gas cap).

Feed bot: it waits on the farm feed `/logs/base` for `Sync(uint112,uint112)` (topic0 `0x1c411e9a...bad1`) on the
old-ARC pair `0xb68f6d54...` and the new-ARC pair `0x2814a97e...` (one filter, 10 + 14 logs in 24 h). On an event it
does ONE `eth_call` of the executor's `probe()` with 13 loan sizes (0.0004-0.113 WETH); when the best gain is above
1.3 x the send's cost cap it sends that size. It re-reads on `gap`, 429, 503 or a connection error, keeps a 300 s
safety poll (the busy VIRTUAL/WETH pair is not subscribed; its drift is seen there) and looks again 4, 15 and 45 s
after a look that saw a gain.

## Competition, last 7 days (blocks 57,600,690-60,624,690; `scratch/r0891/takes7d.txt`)

- 18 arbitrage transactions (197 `migrate` calls), 0.002395 WETH kept in total (about 4.4 USD).
- Operators: EOA `0x9fa50f47...` (13 takes through `0xd3460855...`, `0x84a2b266...`, `0x77865bf6...`), the
  `0xc0ffee..` EOA family through `0x157bad3e...` (4), `0xcb741eba...` through `0xd86db2da...` (1).
- Sizes: 6 takes of 0.00018-0.00062 WETH, 12 takes of 0.00001-0.00005 WETH.
- Fee level: effective gas price 5.1e6-3.9e7 wei (base fee plus almost nothing), tx index 4-272: no priority auction.
- Time from takeable to taken (`scratch/trial-arc-migrate-base/windows.py`, the executor's `probe()` as a code
  override on the state 1 / 5 / 15 / 50 / 150 / 300 / 1,500 / 9,000 blocks before each take; `windows.json`):
  all 18 takes were takeable 50 blocks (10 s) before (17 at the full gain, 1 at two thirds); 13 of 18 also 150
  blocks (30 s) before and 300 blocks (60 s) before; 12 of 18 at 1,500 blocks (5 min), at the same or a smaller
  gain. Minimum window between 10 and 30 s (5 takes: nothing at -30 s, the full gain at -10 s). The incumbents
  react in 10 s or more; the farm's reaction time on Base is 3 s. Negative control inside the same table: 5 takes
  show 0 at -30 s, 7 show 0 at -30 min.

## Loss bound

A lost send costs gas only: about 1.0-1.3M gas at <= 0.2 gwei, under 0.95 USD at 4,000 USD per ETH (in practice about
0.01-0.03 USD at today's fees). Capital 5 USD, no principal (flash loan).

## Read cost

Live: safety poll 288 x 26 CU = 7,500 CU/day; feed: 24 Sync logs a day x 618 bytes x 0.04 = 600 CU plus about
4 CU/min for the subscription = 5,800 CU/day; one probe per event and up to 3 follow-ups = about 2,500 CU/day; about
100 CU per opportunity. Total about 16,000 CU/day = 0.01 USD/day at 1M CU = 0.53 USD. If Base has no free feed
filter (429) the bot re-reads every 60 s instead: 37,000 CU/day. It stops reading at 95,000 CU/day until 00:00 UTC.

## Files

- `bot.py`, `run.sh`, `executor-runtime.hex` (paper code override = `eth_getCode` of the fork deployment of proof.py).
- Executor source: `scratch/trial-arc-migrate-base/contracts/src/TokenMigrateArb.sol`; proof: `scratch/trial-arc-migrate-base/proof.py`.
- Live: `EXECUTOR_ADDR` (or `EXECUTOR_ADDR_BASE`) required; the bot exits without it.

## Result to write after 7 days live or when the 5 USD is spent

One `attempts` row (sends, wins, net) and lead update: `measured` (win rate, net/day) or `blocked_infra`
(how many blocks late, how much fee short).
