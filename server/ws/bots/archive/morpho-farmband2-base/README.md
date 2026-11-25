# morpho-farmband2-base

Base Morpho Blue farm-band liquidation bot (lead 157), reopened per decision
`2026-11-13-blocked-infra-feed-retriage` (the 11-12 archive of morpho-farmband-base
excluded 1-16 s poll-latency windows; with farm-feed a ~60-212 s window is catchable).

## What it waits for

`GET http://127.0.0.1:8546/logs/base?address=<aggregator list>&topic0=<AnswerUpdated>&after=<cursor>&timeout=55`
- aggregators pinned: cbBTC/USD 0xeb3ad4395924b76eb64b3d6ababa0b62875b1a1f +
  0x137233996b6586a110bb7a753248e26cc0307b1b, WETH/USD 0x83f3425a5b32655dc645f7f4e422dd60e9741794,
  cbETH/USD 0x71e021bc2e8a709b72ac7b6036e5b2bf30f263d0 (discovered per run d95b07a8:
  its AnswerUpdated at block 54926149 precedes the cbETH-market capture 54926448);
  the cbXRP-market aggregator 0xfa9ebd1fc381c5babb495bb53664ae9b6665e4e4 is discovered at
  startup and its 2026-11-04 crossing carried zero AnswerUpdated logs - those markets log
  `no-price` and fall back to the safety poll.
- the USD price comes from the latest feed answer at the feed's own decimals scale
  (read once at startup, st.feedDec: the pinned BTC/USD and ETH/USD feeds answer at
  18 decimals, the pinned cbETH/USD feed at 8 - verified with `decimals()` this run);
  the Morpho oracle-wrapper price() padding is NOT a fixed power of 10 (measured
  1e24 for the 18-d WETH/cbETH wrappers vs 1e46 for the 8-d cbBTC wrapper) and is
  never divided by a constant here.
- gap/429/503/502/500/408 or a malformed feed body -> one relay re-read of the
  missed range, the cursor stays until the re-read succeeds (review 1092 blocker 4).

## Capture windows and C-1 eligibility (fix round 2 recount this run: scratch/mb157b-measure.json, scratch/mb157b-windows.json, fork proof scratch/mb157b-proof4.json)

The three counted captures' exact borrowers are now pinned in markets.json (ledger
morpho_blue.liquidation base: block 53486211 borrower 0x63a905f49590b5428e66845b4fb240031a09bbad,
block 54926448 borrower 0xd1a9a065a5edc85a73e7ea81b5032133548235a3, block 56677288 borrower
0x85049883759d4f2e3e9d23364129ddf5bb99dcb1). Their state at the capture's PARENT block
(C-1: market + position getters and the latest pinned Chainlink answer, all read at tag
C-1) and the measured incumbent gas (capture tx receipt gasUsed x the block's baseFee +
the tx's priority fee, ETH at $1934):

| capture | borrower | debt USD C-1 | maxDebt USD C-1 (raw price) | liquidatable at C-1 | gross (wallet delta / bonus estimate) | gas USD measured | eligible->capture |
|---|---|---|---|---|---|---|---|
| 53486211 cbBTC | 0x63a905f4 | 495.547 | 495.117 | YES - fork proof4 at reset 53486210 liquidates: wallet +21.107550 USDC in the same tx; the same state with minProfit = flash x 100 reverts NO_PROFIT | 21.11 (executor at C-1 state, sweep to the wallet) | 0.126 executor-path (602,606 gas x (8.061 + 0.1) gwei); the incumbent paid 1.81 (426,677 x 2.23 gwei) | 1 block (C-1 -> C; 2 s blocks then) |
| 54926448 cbETH | 0xd1a9a065 | 212.001 | 212.146 | no - debt/maxDebt 0.9993 at C-1 | 9.3 (4.384 pct bonus x repaid 211.67) | incumbent 2.81 (174,252 x 8.48 gwei) | 0 block (eligible inside C) |
| 56677288 cbBTC | 0x85049883 | 102.089 | 101.981 | no - fork proof4 at reset 56677287: Morpho reverts "position is healthy" (queued-debt capture) | 4.5 | incumbent 45.55 (1,597,820 x 15.0 gwei - a cascade tx) | 0 block (eligible inside C) |

What decides eligibility is the Morpho ORACLE wrapper price the protocol itself reads
(eth_call price() at tags C-1 and C): A crossed its liquidation threshold in block C-1
(75,774.92 at C-1 vs 75,627.89 at C; threshold 75,703), B and C crossed only IN the
capture block C (2420.73 -> 2415.36 vs threshold 2416.4; 71,246.49 -> 71,098.04 vs
threshold 71,101.4). The captured positions become liquidatable in (or one block before)
the block that takes them: per decision 2026-11-13 (>= 2 blocks counts, 1-block never
counts in EV) the countable pinned-monitor EV is **$0/day** and the route's remaining
gap is SPEED, not detection - 0-block 2 / 1-block 1 of 3. The earlier README windows
(212 / 60 / 184 s) measured the raw feed ANSWER->capture distance (454 / 43 / 9 blocks
before C), which is what a feed bot sees; the protocol-eligibility crossing above is
what it can act on. The raw class EV (1762 captures repaying 100-1500 USD in 7.5 d =
235/day, ~5.5 USD/day gross at the 4.384 pct bonus, attempts:1076) is unchanged; the
221 incumbent wallets take it in the crossing block.

## Borrower coverage and the debt queue (measured this run, lead 157)

- 30 d ledger (blocks >= 54.5M): the monitored markets carry thousands of DISTINCT
  borrowers, not a small whale set: cbBTC 3990 Liquidate events / 3952 distinct
  borrowers, WETH-USD 950/928, cbETH-USD 905/898. The pinned borrower lists are now the
  top-8 per monitored market by 30 d capture count (this run; the old 17-name cbBTC list
  covered 0 of the 30 sampled capture events at the three window-measured blocks -
  coverage is measured ~0 and this is the bot's honest weakness).
- the deployed getters do NOT expose the debt queue's queued principal
  (liabilityHead, queuedDebt(bytes32), queuedDebt(bytes32,address),
  debtSplits(bytes32,address) all revert at head): at the parent block 56677287 of the
  capture 56677288, captured borrower 0x01733de6... showed 461439193 borrow shares and
  8495 collateral (debt ~0.0005 USD) while the block-C Liquidate event repaid
  45389814496044 shares ($51.24) and seized 75236 collateral - the queued principal
  transfers INTO the position inside the capture liquidate() itself. A C-1 polling bot
  cannot see the debt of a farm-band capture; a queued-debt capture becomes detectable
  only when another interaction transfers the queue (or through a storage read the
  incumbent does via extSloads).
- consequence for the paper logs: pinned-borrower checks now show real non-zero
  debt/maxDebt (decode verified: shares x totalBorrowAssets / totalBorrowShares
  reproduces the Liquidate event's repaidAssets to the cent at capture 56677288), and
  LIQUIDATABLE fires on visible underwater debt; the farm-band queued captures will
  show as `no-position`/`check` until the queue leg is solved.

## Reads and cost

Live Alchemy CU/day estimate ~0.19M CU (~0.10 USD at 1M CU = 0.53 USD): feed-delivered
AnswerUpdated for the pinned aggregators (~2000 events/day x ~886 bytes x 0.04 ~ 71K CU)
+ feed maintenance (~4 CU/min ~ 6K) + 5-min safety full scan (288/day x ~28 reads
(3 market getters + 24 pinned position getters + cbXRP fallback) x 10 CU ~ 81K CU)
+ feed-update scans (heartbeat ~3 feeds/hour-day ~ 20K) + gap re-reads. Above ~1M CU/day
needs the human before promotion (not today).

## Fork proof status

CLOSED (review 1092 blocker 2, attempts:1093, manifest fork_evidence): proof3.py on the
shared base fork with the byte-identical artifact + manifest ctor args: send1 success
tx 0x753719e782b3e1c64a66f9fc65a745cb5b2024d15f6891f0d74656d1d8e978cf gasUsed 819743,
owner-wallet USDC delta +21.669873 USD swept in the same tx, executor leftover 0;
send2 same calldata on the now-healthy position reverted
(tx 0x850f0398473bc789f4ad1c6b89ab5081fc5737b47e39e33d98c18266648a2adb).

## Fix round 2 (run 9ca761d0, review 1095 blockers)

1. send-gate sale quote (blocker 1): `bot.js` now quotes the actual seizure
   (`seizedEst = debt x SEIZE_BPS(1.043, measured seized/repaid at the three captures)
   x 10^collDec / (price x 1e4)`) and swaps `amt1 = 999/1000` of it instead of 90 pct of a
   debt-collateral equivalence, so the swap never sells more than the seizure pays the
   executor (the executor caps the pool payment at its collateral balance);
   `profitEst = swap output (bonus-adjusted) - debt` is compared against the gas cap
   `GAS_LIMIT x MAX_FEE_WEI` VALUED AT THE CURRENT pool ETH/USD price (refreshed in
   every scan, not the startup snapshot), and the signed fee cap is logged
   (`gasFeeCapWei`). `maxDebt` divisor fixed to `10^(collDec+18)` (the old divisor
   inflated maxDebt by 1e6 for 18-dec collateral, so liquidatability never fired: the
   paper log had zero LIQUIDATABLE rows before this fix; after it the pinned borrowers
   show debt/maxDebt at the protocol scale and LIQUIDATABLE + the paper simulation run).
   The fork proof (below) reproduces a paper-path send (the same seizure quote, swap
   amount and minProfit the bot builds) with a positive wallet delta.
2. pinned borrowers and detection (blocker 2): the three window-measured borrowers are in
   markets.json and are checked every scan; the C-1 fork proofs above show which of them
   a C-1 detector can reach (A yes, B and C no - queued/crossing inside C).
3. feed cursor commit (blocker 3): `st.lastBlock`, the feed cursor and the answers commit
   only after the range re-read + state scan succeeded (mid-cycle failure rolls back and
   re-reads the same range next cycle); the 429/503 path keeps the old cursor until its
   relay re-read succeeded.
4. per-occurrence economics (blocker 4): the table above is the measured gross/gas/net at
   each capture's own block (incumbent receipts + the executor's fork gas at the block's
   baseFee + a 0.1 gwei tip, ETH at $1934), not `~0.005` and not an upper-bound bonus
   assumption; the countable EV follows the eligibility column (0/day pinned-monitor).

## Fork proof 4 (run 9ca761d0, review 1095; scratch/mb157b-proof4.py, lease taken for the
run only)

Same shared base fork, the byte-identical manifest artifact + ctor args, the FINAL bot
calldata shape (seizure quote 683,345 / swap amount 682,661 at capture A, flash = debt +
0.1 USDC, minProfit 1.00 USDC):
- capture A (reset 53486210): success tx 0x6734f2586642c7f8ae98a31089ef7cd0919b9e20bdcf3ecb27c40997bb914699,
  gasUsed 602,606, owner-wallet USDC delta +21.107550 USD swept in the same tx, executor
  leftover 0; the guard pair at the same state with minProfit = flash x 100 reverted
  NO_PROFIT (tx 0x380f59a5f3785dabf6f05fa6bb6f3c338b27d05fdb100e35c3107c97f95cb922).
- capture C (reset 56677287): the same calldata reverts "position is healthy" (tx
  0xc54961082fd1ef952ff1a6203cb0c70ee2bcad45d1de0c1a96455b893a23749a) - the queued-debt
  capture is not C-1-liquidatable, matching the measurement above.
