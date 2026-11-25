---
type: method
chains: [bsc, polygon, hyperevm]
protocols: [solv_xsolvbtc_pool, cakepie, longinus_lgns]
author: meta/opus
updated: 2026-11-23
---
# Executor route census: every route a general arbitrage executor earns on, by the events in its transactions

**Conclusion.** A general atomic-arbitrage executor that the farm already meets on one class runs dozens of other
routes, and its transaction list is a ready-made list of public redemptions with a pool next to them. List every
transaction sent to the executor for 7 days, group the receipts by the events that are not transfers or swaps, name
the emitters, and read one receipt per unknown group. Two runs on BSC on 2026-11-22 found two bots and one blocked
lead: the YoloVerse dividend trigger (bot `trial-yolov-div-bsc`) and the FUSD exchange (blocked_infra) from executor
`0xf38c67a7` (run fe02da02, attempts:3835 / 3837 / 3838), and the Solv xSolvBTC instant withdraw from executor
`0x3ee0a37f` (run ef082019, attempts:3856 / 3857 / 3859, bot `trial-xsolvbtc-redeem-bsc`). About 12k CU for 635
transactions (attempts:3838; the 1,207 of the second run were not metered separately). It complements
`methods/payout-address-census.md`, which needs a fixed native payout address; this one needs only the executor's
address.

## How

Scripts in `scratch/rfe02/` (copy them; they write next to themselves):

1. `bsc_exec_txs.py <chain> <executor> <blocks> [pages]`: `alchemy_getAssetTransfers`, category `external`,
   `toAddress` = the executor, `excludeZeroValue: false` (zero-value calls are listed; `explorer txs` does not serve
   bsc). Writes `txs-<chain>-<executor prefix>.json`.
2. `classify.py <chain> <txs json>`: every receipt, grouped by (emitter, topic0) of the events that are not Transfer /
   Approval / Swap / Sync / Deposit / Withdrawal. Writes `class-...json`.
3. `names.py <chain> <class json> [n]`: `name()` / `symbol()` of each emitter and event names from the signature
   database (untrusted names; several consistent ones are evidence).
4. `scratch/redcd/kbgrep.py <address prefix>...` on every emitter: half are known classes.
5. `pnl.py <chain> <class json> <emitter prefix>...`: the sender's native balance change per transaction of a group.
   The list of blocks is as useful as the sum: takes in consecutive blocks are one gap being split or raced; takes
   minutes apart at the same net are a threshold taker with room under its line.
6. One receipt per unknown group (`scratch/ref08/multi.py <chain> <tx>...` prints the transfers of several
   transactions), then `scratch/ref08/tr2.py <chain> <tx>` (every state-changing call with its input) to rebuild the
   route, and `scratch/ref08/evscan.py <chain> <emitter> '<Event(sig)>' <blocks> <page>` to list every taker of the
   paying contract's event, not only this executor.

## What decides whether a route is worth a bot

The operators of these frameworks fire at a fixed line (about 0.00008 BNB net on BSC) with **fixed small lots** and a
**generic route** (flash loan of a base token, then swaps in and out). That leaves two openings a purpose-built
executor can use:

- **A shorter route.** The xSolvBTC incumbent borrows BTCB, buys SolvBTC, buys xSolvBTC, withdraws, sells SolvBTC.
  A flash swap on the xSolvBTC / SolvBTC pool itself needs no loan and no entry swap; a gain of 0.0002-0.0004 BNB then
  stands all week below the incumbent's line.
- **The whole gap in one transaction.** After a 0.0098 xSolvBTC sell the incumbent took 11 lots over 140 s (0.0042 BNB
  in total); one transaction sized from a grid at the parent of its first take pays 0.0078 BNB on the fork.

Measure both with the new executor's own `probe()` as an archive `eth_call` with a code override at the blocks around
the incumbent's takes (`scratch/trial-xsolvbtc-redeem-bsc/series.py <block> <offsets...>`): it shows when the gap
opened, what was left after each incumbent lot, and what stands at head.

An incumbent taking a route does not make it allowed: skim-type routes (a pool's balance above its booked reserve,
taken via `skim` / `sellBase` / `swap`) are out under S (human 2026-11-23, `methods/skim-excess-sweep.md`).

## What the two BSC executors held (7 days to 2026-11-22)

- `0xf38c67a7` (635 txs): attempts:3838.
- `0x3ee0a37f` (1,207 txs, 281 groups, actors:373): attempts:3859. Per route the sender nets 0.0003-0.047 BNB a week.
  Built: xSolvBTC. Known: CKP, CMC20, tMantaBNB, XUSD, AUSD, FUSD, RYDEME. Read and left as cents: WELEPHANT unwrap,
  old RACA -> new RACA migration, CDSU SetToken redeem, BTOP20 index join, NVDAon `RWASold`. Not allowed: DGC staking
  rewards claimed through throwaway contracts, Flap dividend tokens.
- **A protocol closed as "no caller reward" can still hold the route.** Solv on BSC had five closed `protocols` rows;
  none named `XSolvBTCPool.withdraw`. The census finds the contract by its event, not by the protocol's name.

## Run 775e819a, 2026-11-22 21:40Z (attempts:3873)

- bsc `0x742414b7` (449 txs) and `0x1836532f` (272 txs): **single-route executors**, every transaction is the CMC20
  Folio round trip (lead 317). A census of an executor built for one class finds nothing; check with one `classify.py`
  run (one event group = stop).
- polygon `0x0329e512` (sender `0x4f8aed90`, 445 txs, actors:374): pool-to-pool cycles for 0.02 USD a take (358.65 POL
  = 27 USD in 7 days), except one route: the **rebase surplus** of sLGNS in a DODO pool (lead 415). A rebasing token in a
  pool that books reserves leaves `balance - reserve` after each rebase; DODO's `sellBase(to)` pays it to the next caller
  even with nothing sent in. The timing is exact (every 14,400 blocks). **Not allowed: skim type, S (human 2026-11-23,
  `decisions/human/2026-11-23-s-no-skim-rebase-surplus.md`); lead 415 dead_end.**
- bsc `0xd8f06a1f` (sender `0xd7550844`, the same framework as the polygon one; 3,000 txs, attempts:3874): pool cycles
  only (prop AMMs, Few-wrapped tokens, tokenized stocks), 0.01-0.08 USD a take, stopped at block 134,639,511.
- hyperevm `0x0418f780` (the `0x43637877` shop, 3,000 txs = 1.65 days, attempts:3875): every route with a mechanism
  (Ensemble vault shares, ICHI vaults on Nest) already has a lead and a farm bot; the rest are pool cycles.
- base `0x79f630cc` is single-route (WETH / USDC / cbBTC cycle, actors:318): skip it.

### Schedule detector (offline, no RPC)

`scratch/r775e/periodic.py <class json>...` reads a `classify.py` output and prints the event groups whose takes are
evenly spaced in blocks (bursts within 200 blocks count once; at least 5 episodes; 60 pct of the gaps a whole multiple
of the median gap). Evenly spaced takes = a schedule (rebase, epoch, dividend trigger): the kind of route whose time
the farm knows in advance. On the five saved censuses it prints exactly four routes: sLGNS (14,400 blocks, polygon,
closed under S: skim type), YoloVerse (28,800, bsc, `trial-yolov-div-bsc`), the PAP Flap dividend (8,000, bsc, closed
under S) and GLCS PairBurn (about 49,000, bsc, cents). Run it right after `classify.py`, before reading receipts by
hand; for a hit, read the state one block before a take and one block before the previous schedule point to see what
changed.

- bsc `0x0000000000be226a` (actors:243; 3,000 txs = 19 h, 533 groups, attempts:3877): the RYDEME-framework token DRA
  (549 txs, builder-tipped bundles, lead 379), Flap tokens (closed under S), a self-made sandwich of a token's public
  buyback (ANTB, not allowed), launch one-offs; the rest pool events. For a 7702 wallet the sender's balance change is
  not a P&L (payouts go to the wallet and the builder): use group sizes.

Every general executor named in the KB has now been read once. A new run is worth it only for a new executor
(`actors` rows added later) or a window after a visible change in an old one.

## Run ca2392f0, 2026-11-23 00:40Z (attempts:3917, 3919)

- **Finding executors to read**: `scratch/rca23/multiswap.py <chain> <blocks back> <page> [top] [receipt cap]` lists the
  contracts whose transactions swap in two or more pools (topic-only Swap logs of V2 / V3 / PancakeV3 / V4 / Solidly,
  a random receipt sample grouped by `tx.to`, with sender count and code size). One or a few senders and thousands of
  transactions a week = a speed pool arber (optimism `0xe0a118c6`, `0xb8965f44`, `0xbed703ac`: 283 event groups, all
  pools; nothing to copy). Tens to hundreds a week = worth a route census.
- **Profit per route when the executor pays a fixed address in a token**: `scratch/rca23/payout_by_group.py <chain>
  <class json> <token> <payout> <blocks back>` joins the token's Transfer logs to the payout address with the
  `classify.py` groups and prints sum, median, largest take and the number of episodes per emitter. The sender's
  native balance change (`pnl.py`) only shows gas for such an executor.
- avalanche `0xd1f6ca07` (836 txs in 450,000 blocks, payout `0x56435da7` in WAVAX) and `0x777e0fc6` (2,831 txs): pool
  cycles, Aave v3 / Benqi liquidations and the bridge migration the farm already has. **One take was 929.9 of the
  1,031.5 WAVAX paid in the window** (a venue selling BTC.b far under the market, taken at tx index 5): read the
  largest take before quoting a route's sum. Two routes with a mechanism, both episodes and not built: Benqi qiAVAX
  minted and sold on a Uniswap v4 pool (12 takes in one 23-block burst, fee war) and 1inch limit-order fills (orders
  only from the keyed 1inch API).
- elysium: the first atomic arber on the chain (`0x127db0c0`, v4 pool -> V3 pool -> v4 pool) pays about its whole gain
  as fee for tx index 1 of a 100-200 ms block. Pool arbitrage there is a race.
