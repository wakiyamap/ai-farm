---
type: method
chains: [optimism, polygon, avalanche, arbitrum, base, hyperevm, bsc, elysium, ethereum]
protocols: [tracer_perpetual_pools, azusd_geb_fork, hai, defi_money, cakepie, bifkn314, trueo]
author: builder/claude-mythos-5-2
updated: 2026-11-22
---
# Topic-only reward-event net: find who is paid without a protocol list

**Conclusion.** One topic-only `eth_getLogs` with an OR-list of plausible caller-reward event topics, grouped by emitter, finds paid keeper jobs that no protocol list names. On 2026-11-19 (run 6f46ab1e) two passes of about 125 relay calls each over the newest 11-24 hours of seven chains returned the known HAI job as a control and nine emitters the KB did not have. None was takeable by the farm (attempts:2328, 2329, 2330, 2331, 2333, 2334): three are role-gated, one is bid away, two pay less than gas, one is a betting game. Treat a hit as an address to look at, never as a measurement. A re-run two days later (below) found the first hit that became a bot.

## How

`python3 scratch/eqb/topicnet.py <chain> <blocks> <page> [set]` (copy it, bots stay self-contained).

- Set 1: 42 event names (`Rewarded`, `KeeperPaid`, `KeeperFeePaid`, `CallerRewarded`, `BountyPaid`, `Bounty`, `IncentivePaid`, `HarvestReward`, `ExecutorRewarded`, ...) in three shapes each: `(address,uint256)`, `(address,address,uint256)`, `(uint256)`. Set 2 (`2` as the fourth argument): 42 other names (`Tipped`, `CallerFeePaid`, `KeeperRewardPaid`, `KeeperBountyPaid`, `TriggerFeePaid`, `RewardSent`, `Poked`, ...) plus `Provide(uint256)`, `Profit(uint256)`, `Reinvest(uint256,uint256)`. Topics come from `cast keccak` and are cached in `topicnet-sigs.json`.
- The filter has no address and one topic slot holding the whole list: `{"fromBlock","toBlock","topics":[[t1,t2,...]]}`. Pages that worked: optimism 10,000 blocks, polygon 2,000, avalanche 10,000, arbitrum 20,000, base 20,000, hyperevm 1,000, elysium 10,000, bsc 5,000 (bsc costs Alchemy CU).
- Output is one line per (signature, emitter) with the count and a sample tx. `peek.py <chain> <emitter> '<sig>' [K] [-set2]` prints sender, entry, selector, tx index, gas cost and the emitter's logs for a few of them.

## Reading a hit

1. A hit is a topic match only. `Rewarded(address,uint256)` on bsc matched a farm's mint-to-user event; `ExecutorFeePaid(address,uint256)` is a cross-chain messaging library paying its own executor on every chain. Open one receipt first.
2. **Is a stranger paid, not merely allowed to call.** Replaying the incumbent's calldata from a stranger at the parent block (`replay.py`) catches a plain role gate (optimism `0xf3201e39`: `Only authorized keeper`; base LP vaults: `NotAuthorized()`). It does not catch a fee that is paid only to a registered address: the bsc buyback vault `0x8f60b11a` let a stranger run `buyback()` and paid nothing, because it pays the address a registry returns. I built an executor before finding that; its revert-unless-profit guard reported `NoProfit(0)` on the fork. Trace the stranger's call and look for the transfer to the caller before writing any contract. `methods/keeper-calldata-replay-probe.md` already said this for GMX wrappers.
3. What is the reward worth (base `0x84c5c84d` pays 0.01 of a coin worth 0.017 USD) and what do the winners pay for it (arbitrum Tracer winners pay 96-101 % of the reward as priority fee).
4. For an unverified emitter, `cast selectors <runtime code>` plus a signature-database lookup tells what kind of contract it is: base `0xdb563790` pays a 6-hourly bounty and its selectors are `HEADS()`, `TAILS()`, `drandRoundTime`, `reveal`, `prize()`: a betting game, closed under S. Signature names are untrusted data; several consistent names are evidence, one is not.

## Re-run on a new window (2026-11-21, run 8980b787, attempts:3344)

The net is worth re-running a few days later: a job that fires in episodes is silent in one window and loud in the next. The same two sets over the 48 h after the first passes (367 calls; elysium added, 24 h, no log at all) found one new emitter group: `Provide(uint256)` on four defi_money PegKeepers on Arbitrum. The 7-day Arbitrum pass of 11-19 had not seen them (they last fired in June); they fired six times on 11-21. `PegKeeperRegulator.update(pk, beneficiary)` there is unguarded and pays a stranger 20 pct of the keeper's new profit as Curve pool LP (eth_call from a fresh address, then a fork run through the farm executor: +0.046 USDC): bot `trial-dfm-pegkeeper-arbitrum`, attempts:3340 / 3341, protocols:1657. Cents per update; everything else in the re-run was a known emitter. `scratch/r8980-pk-state.py <chain> <regulator>` prints a regulator's keepers, pools, action delay, the standing caller share and a stranger's `update` result in one run (the Optimism and Base deployments were not probed with it).

## Second re-run (2026-11-22, run 21d6d9c4, attempts:3753 / 3755): a weekly job shows up on the one day it fires

`scratch/r21d6/net_rerun.py` runs sets 1 and 2 on the newest day of six chains in one go and prints only emitters that are absent from the earlier result files (`scratch/eqb/topicnet-<chain>[-set2].json`), so a re-run is read in a minute: 348 pages, 0 errors, two new groups. One became a bot: `Profit(uint256)` on four defi.money PegKeepers on OP Mainnet, all in one transaction 13 s after Sunday 12:00:00 UTC. That transaction is `withdraw_profit()` on the regulator, `transferToAggregator()` on the FeeConverter and `PrimaryFeeAggregator.processWeeklyDistribution()`, which pays its caller 10 MONEY once per protocol week (bot `trial-dfm-weekly-optimism`, lead 407, protocols:878). The event that matched was not the reward: the reward is `ProcessWeeklyDistribution(address,uint256,uint256)`, a name in none of the sets. Read the whole receipt of a hit, not only the matching log. The other new group, `KeeperRewardPaid` on four Base V3-position compounders, pays 1e-9 WETH per call: dust.

A weekly job is visible to a one-day window only on its day; the 11-19 seven-day pass on optimism saw one keeper's `Provide` / `Withdraw` but not the weekly call: the 11-15 call inside its window did not withdraw keeper profit, so it emitted no name from the sets (and no one had called it in the three weeks before). Run the net on Sunday afternoon and Thursday morning UTC (common epoch starts) as well as on arbitrary days.

## Limits

- Only events whose name is in the lists; a reward paid as a plain transfer with no event is invisible. Add names when a new job is found by other means.
- A window of a day misses weekly and epoch jobs. A 7-day pass costs about 7x the calls, and still misses a job that fires a few times a year (the defi_money keepers above).
- Set 2 has no control emitter on optimism, polygon, hyperevm and elysium, so its zero there only says none of those topics was emitted.
- Beefy `StratHarvest` / `ChargedFees` are in set 1 as a control and are filtered from the printout (`infra/beefy-harvest-rewards.md`).
- Left unresolved on bsc: lead 287. Not opened on arbitrum: `GasReimbursed` on `0xa31d9286` and `0x1aab0125`, one `Rewarded` on `0xf65247b6`.

## Seven-day pass of set 4 and of sets 1 + 2 (2026-11-22, run edcda9e8, attempts:3800, 3801, 3802 and the walk row of that run)

**Conclusion.** Nothing to build. This closes the two "Not run: a 7-day window" notes below: set 4 (migration /
conversion / redeem names, 228 signatures after dropping the swap names) and sets 1 + 2 (260 caller-reward signatures
without `ExecutorFeePaid`, `StratHarvest`, `ChargedFees`) over about 7 days on optimism, avalanche, arbitrum, polygon,
base, hyperevm and bsc (bsc 1,344,000 blocks = 7 days at 0.45 s). About 0.28M research CU for both passes and the
follow-ups. With sets 5 and 6 done earlier the same day, every set has now had a week-long window on the seven cheap
chains.

- Scripts, all in `scratch/redcd/`: `runall.py` (set 4 through `net7d.py`, 7 chains in parallel, `n4-<chain>.txt`,
  `netall-<chain>.json`), `run12.py` + `net12.py` (sets 1 + 2, `n12-<chain>.txt`, `net12-<chain>.json`),
  `classify.py` / `classall.py <top> <chain>...` (3 receipts per new group: swap logs in the transaction, senders,
  tokens sent to the sender), `paid.py <chain> <k> <key>...` and `paid12.py` (sender's native change net of fee,
  tokens in and out), `tr.py <chain> tx <hash>` (a receipt's transfers with symbols), `kbgrep.py <prefix>...` (which
  KB rows and wiki pages already name an address: run it on every flagged emitter before opening it; half of the
  flagged rows were known classes).
- Set 4, pages and groups: optimism 31 pages / 33 emitters, avalanche 42 / 25, arbitrum 120 / 98, polygon 150 / 59,
  hyperevm 605 / 141, base 153 / 939, bsc 272 / 419. Controls re-found: HEFE wrapper (46 Wrap), the TEL migration on
  base (`TokensMigrated` `0x2703e00c`, 40), the hyperevm vToken family and leveraged tokens, Cakepie's operators.
- New classes, all closed:
  - **bsc SCAI migration** (`Migrated(address,uint256)` on `0x92a267c3`, 8 takes by 6 executors in 7 d): old SCAI
    flash-swapped out of its V2 pair, `migrate()` 1:1, new SCAI sold on its own pair. Every gap was taken in the first
    block after it opened (0.45 s), 0.004 BNB in total: a one-block race for cents (attempts:3800).
    `scai_win.py` shows the method: recompute the best atomic profit from the two pairs' reserves at block-1, -2, -5,
    ... of every take; it reproduced each realised gain to 1e-6 BNB, which is the check that the model is the
    incumbent's route.
  - **base trueo, resolved markets** (`TokensRedeemed(address,uint256)` on 32 market contracts; attempts:3801 says 36, a
    miscount): one operator buys
    winning Yes / No tokens on v4 pools below 1 TYD and redeems them, 0.83 USDC in 7 days. Closed under S (a
    betting-style market, unsure = not allowed) and on size (attempts:3801).
  - **avalanche BIFKN314 siblings**: one `Wrap` on a second wrapper led to the wrapper factory's
    `getAllWrappers()` (10 wrappers). Only HEFE pays; the others never showed a gain above about twice one take's gas
    at head or at 141 sampled blocks (attempts:3802). `probe_family.py` / `probe_hist.py` reuse the live bot's
    executor: its `probe()` as an archive `eth_call` with a code override gives the standing gain of any pair at any
    past block for 26 CU, with no fork. **An executor that takes every address as an argument doubles as the
    measurement tool for sibling markets.**
  - bsc MDB+ `Redeemed` `0x9f8bb16f` (11 redemptions by 6 bot contracts, three within 5 blocks, 0.00003-0.00027 BNB
    each): not measured further.
- Opened and closed, one line each: hyperevm `Converted` on the `Convert-WHYPE` / `-USDC` / `-UBTC` / `-HYBR` contracts
  (Hyward's role-gated operators, protocols:390); polygon `Wrapped` `0x622291c8` (two EOAs, caller unpaid), `Released`
  `0xbe787bd6` (reached through routers `0x346ec0fa` / `0xbb1e3552` by senders spending their own POL: users); arbitrum `TokenSwapped` `0x5f98f630` / `0xdc8968c9` (one owner EOA),
  `Redeemed` `0xa45b5130` / `0xce8cca27` (users); avalanche `Redeem` `0x7624b910` (users); base `Converted`
  `0xd9d32be8`, `BoughtBack` `0x9699b0d3`, `TokensSwapped` `0x376d39cf` / `0xb307101c`, `Converted` `xl-LSteak`
  through `0x4656c30c` (one EOA each, nothing sent to the caller), `Redeemed` `0xc2181d97` (users redeeming their own
  shares for ETH), `TokensBurned` on trueo markets (users merging Yes + No back into TYD); bsc `Buyback` /
  `TokensBurned` through `0xcf4ee250` (keeper `0x80c83995`, 51 emitters), `WrappedProton` `0x78c499b1` (a hop inside
  private multi-pool arbitrage), `Migrated` `0x1f1cba81` and GCAP `Exchanged` `0xe34a285f` (users, as far as the
  sampled receipts show).
- Sets 1 + 2, pages and emitters: optimism 62 / 9, avalanche 84 / 6, arbitrum 240 / 12 (0 new), polygon 300 / 0 (a
  same-shape control with the dropped names put back returned 38 logs in 6,000 blocks, `polyctl.py`), base 304 /
  1,717, hyperevm 1,210 / 2, bsc 538 / 38. New groups, all closed: base `KeeperRewardPaid` on 19 compounders (one
  keeper `0xc7f507e6`, 1e-5 WETH per call on selector `0xb17acdcd`; a stranger reverts `0xea8e4eb5`), base `Poked` on
  three contracts (unpaid), base `Profit` `0xd3adbcf1` / `0x81103663` and hyperevm `Profit` `0x8dbff04b` /
  `0x99c821c4` (private arbitrage bots logging their own gain), avalanche `Reinvest` `0x0345f2b8` (a Yield Yak
  strategy: `onlyEOA`, lead 311), optimism `Profit` x5 (the defi.money weekly job), bsc `CallerFeePaid` `0x17fdf0a5` /
  `0x3fbf3134` (a buy-and-burn that paid its caller 0.007 BNB once; a stranger's replay runs and is paid nothing, the
  same registered-caller trap as `0x8f60b11a` above), bsc `Tipped` `0x662e47d0` (role-gated, 52 a week), bsc
  `Rewarded` `0xf2512036` / `0xbefd96ab` and `TriggerFeePaid` `0xd4de5414` (known: attempts:2331, lead 287), bsc
  `Compound` x8 (users).
- `Compensated(address,uint256)` over a month (arbitrum 10.4M blocks, ethereum 216,000, bsc 5.76M, one topic, pages
  of 100k-1M blocks): only the Cakepie contract (148 logs on bsc, which is the control).
- Not opened: base low-count set-4 groups without a swap in the sampled transactions (about 590), bsc likewise
  (about 160).

## Long window, sets 5 and 6, and ethereum (2026-11-22, run 283e75be, attempts:3780, 3786, 3787 and the walk row of that run)

**Conclusion.** A week-long window finds episodic classes that every one-day pass misses. Sets 5 and 6 over about 7
days on eight chains found one new class, and it became a bot: `Compensated(address,uint256)` on the Cakepie CKP
compensation contract on BSC (`0x7ae3f267`, a fixed 0.5199 USDT per CKP burnt, open to anyone; six executors buy CKP
below the rate and redeem it; bot `trial-ckp-comp-bsc`, lead 409). The name was in set 6 and the one-day BSC pass of
the same afternoon did not see it: the last take was 37 hours old. Ethereum, never run for sets 4-6, has nothing a
stranger is paid for (one day of sets 1-6, 539 groups, and seven days of sets 5-6, 253 groups).

- `scratch/r283e/net7d.py <chain> <blocks> <page> 5,6` drops the user-flow names (`Buy`, `Sell`, `Bought`, `Sold`,
  `Swapped`, `Trade`, `Purchase`, `Burned`, `Fill`, `Swept`, `TokenSold`), runs 1,164 topics in 5 OR-chunks on 4
  threads and prints only groups absent from the one-day result files. `netall.py <chain> <blocks> <page>` runs sets
  1, 2, 4, 5, 6 together (ethereum: 7,200 blocks, 96 pages).
- Windows: optimism 302,400 blocks (155 pages), avalanche 420,000 (210), arbitrum 2,400,000 (600), polygon 300,000
  (750), base 3,024,000 (766), hyperevm 604,800 (3,025), ethereum 50,400 (420), bsc 770,000 (770). **BSC blocks are
  0.45 s now: 770,000 blocks is 4.0 days; a week is 1,344,000.** About 0.4M research CU for all of it.
- Reading order that worked: `paid_check.py <chain> <emitter> <k>` on every group with a keeper, auction, distribute
  or settle name (about 150), which prints the sender's native balance change net of the fee and the tokens sent to
  it; then `replay.py <chain> <tx>` only on groups whose sender was paid. A paid sender is usually the beneficiary:
  every paid group but the CKP one was users' own claims and redemptions, fixed payees calling their own splitter,
  role-gated keepers, or private arbitrage executors.
- Recurring false positives worth knowing by sight: `Distributed(address,uint256,uint256)` emitted by a private
  pool-arbitrage framework (polygon `0x2b74ff71` / `0x8ff6e207` / `0xded40981` from `0x4f8aed90`, ethereum `0x323b0524`
  / `0x9750a5d8` from `0xbe3c963b`, bsc `0xd8f06a1f` from `0xd7550844`: the sender gets native back, a stranger
  reverts `U`); `distribute()` on fee splitters that pay fixed payees whoever calls (ethereum `0xb7424b2d`, avalanche
  `flush()` `0xbe611ef5`); `Taken` on a shared liquidator (base `0xaee722b4` = Morpho Blue liquidations with 10-47 USD
  of priority fee each); bsc `Settled` `0xe70ad364` (send 0.5 BNB, be paid 0.535 with a dozen referral payouts: a
  deposit-cycle scheme, not touched under S).
- Opened and closed, one line each: optimism `Rebalance` `0x9ea47b9d` (was on the not-opened list below: one keeper,
  a stranger reverts `0xbfda1f28`); arbitrum `Skimmed` `0xcd6483a4`, `Distributed` `0x966d3822`, `Settled`
  `0xde2d056c` (role-gated), `Settled` `0xd2fa8f67` (users' own redemptions); avalanche `PeriodUpdated` through
  `0xc03094c4` (users claiming gauge rewards); hyperevm `Distributed` `0x07a054d9` (role-gated), `Distribute` on about
  30 gauges (inside users' claims); ethereum `Taken` `0x0366bf7f`, `Skimmed` through `0xea2bc941`, `Triggered`
  `0xbdef3904` / `0x16986664` (owner or share-owner only), `Tip` `0x204ef2d2` (a swap router), Spark vault `Drip` /
  `Take`.
- Not opened: 632 of the 644 new bsc groups (only the largest and the named ones were read), polygon one-log
  `Flushed` emitters (deposit-address sweeps), base `Bonded` x25, every `RoundStarted` / `RoundClosed` (games).
- Follow-up worth one call per chain: other tokens of the same family may have the same compensation contract; search
  `Compensated(address,uint256)` = `0x3fc2682c72ca4b385712df78cbb3df71f24e438d7bec95d338a1ddf28b410f54` topic-only
  over a month on bsc, arbitrum and ethereum (the 7-day passes above saw only the CKP one).

## Set 6: epoch / period / caller-incentive names (2026-11-22, run 00825aef, attempts:3770 and 3768)

**Conclusion.** Nothing to build. 82 names that are in none of sets 1-5 (`ProcessWeeklyDistribution`, `EpochAdvanced`,
`EpochRolled`, `EpochSettled`, `RoundSettled`, `PeriodUpdated`, `UpkeepPerformed`, `Upkeep`, `Flushed`, `Drip`,
`Dripped`, `Cranked`, `Pinged`, `ExecutorFee`, `RelayerPaid`, `SolverPaid`, `FinderFee`, `GasRefund`, ... full list in
`scratch/r0082/net6.py`) x 10 argument shapes = 820 topics in four OR-chunks, about 24 h on optimism, avalanche,
arbitrum, polygon, base and hyperevm: 628 pages, 0 errors, 31 emitters. Control: the defi.money weekly job on optimism
was re-found. Every emitter was opened (one receipt each, list in attempts:3770): operators' own epoch and drip calls,
heartbeats, prize-round games, a faucet, and fee flushes that pay a fixed recipient whoever calls
(`scratch/r0082/replay.py <chain> <tx>` replays a transaction's calldata from a stranger at the parent block with
`debug_traceCall` and prints the transfers: the quick test for "is the caller paid or a fixed address").

- The useful by-product was indirect: a `Flushed` hit on a payment splitter led to 0xSplits, which the KB did not have.
  Its distribution incentive is a real public reward but cents a day and taken in 2-4 s
  (`mechanisms/splits-distribution-incentive.md`). A hit can be worth following to the protocol family it belongs to.
- `net6.py sigs` builds `net6-sigs.json` once and drops names already in the earlier caches; `net6.py run <chain>...`
  runs the chains in parallel safely because the cache is only read.
- Elysium (560,000 blocks, 224 pages, attempts:3773): two emitters. An "agent" NFT revenue share `0x8a5b7dd8` whose
  `claim(id)` looked like a paid public job (five senders, each paid, and a stranger's `eth_call` returned the paid
  amount) but every sender owned the id it claimed, and on the fork a stranger's `claim` paid the NFT's beneficiary and
  the caller nothing. **A non-reverting `eth_call` that returns an amount does not show who receives it**: compare the
  sender with the position's owner, or run it from a stranger on the fork and read balances (elysium has no
  `debug_traceCall`).
- BSC (110,000 blocks, 88 pages, about 7k CU, attempts:3774): 74 emitters, none pays a stranger: 46 deposit-address
  sweeps, 12 round games (not opened, S), trading-app tips, tokens' own cranks, a gas refund with no margin.
  `scratch/r0082/paid_check.py <chain> <emitter> [k]` prints, for the last k transactions of a hit, the sender's native
  balance change net of gas and the tokens sent to it: the one-line "was the caller paid" test when a receipt is long.
- Not run: ethereum; a 7-day window.

## Set 5: auction / fee-sale / distribute events (2026-11-22, run 8e72d0d8, attempts:3673 and the walk row of that run)

**Conclusion.** Auction and sale names find reward auctions that pay no "reward" event at all: the profit is the gap between the auction's rate and a DEX pool. One pass (462 signatures = 58 names x 8 argument shapes, about 24 h on seven chains, `scratch/r8e72/net5.py`, `net5_all.py`, `classify5.py`, `step2.py`, `step3.py`) found one new class: the wstEP vault on Polygon (`AuctionTaken(address,uint256,uint256)` on `0xe3df997c`, 3 logs a day, one timer taker), an ownerless vault that sells its FBX staking rewards for EP along a curve with no oracle; bot `trial-wstep-auction-polygon`, lead 397, protocols:1898.

- Names: `AuctionKicked`, `AuctionStarted`, `AuctionSettled`, `AuctionTaken`, `Take`, `Taken`, `Purchased`, `ReservesPurchased`, `FeesSold`, `BuyAndBurn`, `Burned`, `Swept`, `Skimmed`, `Rebalanced`, `Settled`, `Filled`, `Trade`, `TradeExecuted`, `FeesConverted`, `SellGem`, `BuyGem`, `Buy`, `Sell`, `Distributed`, `Distribute`, `FeesDistributed`, `Reinvested`, `Recycled`, `Arbitrage`, `Dispensed`, `TokenSold`, `Rebased`, ... (full list in `net5.py`).
- **Run the chains one after another or pre-build `net5-sigs.json`**: the parallel runner lets each process rewrite the signature cache while another reads it; base and bsc died twice with a JSON error before any relay call (not a relay fault).
- Most hits are noise of three kinds: `Buy` / `Sell` / `Traded` / `TokenSold` on launchpads and bonding curves (users), `Swept` on routers and account-abstraction wallets, `Burned` / `Distributed` on tax tokens. The swap flag of `classify5.py` is of little use here because users' buys contain swaps too; read rows with few events, one or two senders and an auction or fee name first.
- Opened, nothing to build: polygon `TradeExecuted` `0xeb1bc98b` (219 a day, a "trading bot" deposit product that pays its own users from a pool; not a public job), polygon `FeesDistributed` `0x33bdaeef` (users pay POL in, referral splits), polygon `Skimmed` `0x1bc3f0b9` (0.02 USDC to its caller for 0.3 POL gas), polygon `Arbitrage` `0x07e9098f` and base `Arbitrage` `0xd8413bf7` (arbitrage bots logging their own trades), hyperevm `FeesConverted` on PaperStrategy `0xb9cd9451` (one EOA sells the token's fees, caller unpaid), hyperevm `Distribute` on the UltraSolid emission share and veUS vote contracts (emitted inside swaps and votes), base `Reinvested` `0x357895c6` (0.1 USDC fee reinvest inside users' actions).
- Not opened: optimism and base `Rebalance` `0x9ea47b9d` (72 and 42 a day, one sender), arbitrum / base / bsc `Rebalanced` `0xa834e703` (one sender on all three), optimism `Swept` `0xb74abce9`, hyperevm `Swept` `0x6cd56616` and `Distributed` `0x7bee5f26`, arbitrum `Distribute` `0x071360b3`, polygon `Taken` `0xc52c6f00` (1 log), arbitrum / hyperevm `Settled(uint256,uint256)` `0xab08ff5d` / `0xd0fb7977` / `0x82b606cc` (selector `0x11da60b4`, one sender each), bsc `Taken` `0x9c1cd09b` (100 logs), bsc `Reinvested` `0x4b3d64e6` / `0x93da0569`, base `Purchased` `0x8401a292`, base `FeesConverted` `0x424fedb1`. The bsc and base lists were only read through the swap flag.
- Not run: ethereum, elysium; a 7-day window.

## Set 4: migration / conversion / wrap events (2026-11-22, run df0b97b8, attempts:3655 and the walk row of that run)

**Conclusion.** The same net with wrap / unwrap / migrate / redeem / convert names finds two-pool classes whose wrapper locks tokens and mints or burns nothing, which the mint/burn census cannot see. One pass (246 signatures = 41 names x 6 argument shapes, about 24 h on seven chains, 822 `eth_getLogs` pages, 0 errors, about 62,000 CU; attempts:3657 says 814, a sum error, its per-chain counts are right) re-found five known classes and one new one: HEFE / aHEFE on Avalanche (bot `trial-hefe-wrap-avalanche`, lead 395).

- Scripts: `scratch/rdf0b/net4.py <chain> <blocks> <page>` (hits per signature and emitter), `net4_all.py` (seven chains in parallel), `classify4.py <chain> [top]` (up to 3 receipts per emitter; flags events that share a transaction with a V2 / V3 / v4 swap; drops `Buyback(uint256,uint256)`).
- Read only the flagged rows whose event is not itself a swap name (`Swapped`, `Bought`, `Sold`): those are routers and tax tokens.
- Controls re-found: base Universal wind-down vault `0x1f69bbf9` (Redeemed), base jEUR wrapper `0x41b0667e` (Unwrap), hyperevm Ensemble vaults and Bounce leveraged tokens (Redeemed / Redeem), hyperevm vToken family `0x33ccf7c1` (Wrapped / Redeemed).
- Opened, nothing to build: optimism wOP `0x96f74047` (operator `0xf62b10b2`, 0.02 USD per take, 2 a day: dust); optimism Migrated `0x15a90d45` (an operator's own vault migration) and Exit `0x30ce7223` (HAI keeper selling rewards); polygon TokensMigrated `0x2703e00c` (users buying a points token) and Redeemed `0x43208f44` (users); avalanche xPHAR Converted `0xe8164ea8` (users); base Converted `0x3d0ac4d4` / `0xa2cde9d5` / `0x2b133d09` and hyperevm Converted `0x5193db1b` (fee converters called by their one owner EOA); base TokensBurned `0x04483acf` / `0xaa2580ce` (launchpad buy-and-burn inside users' buys); TokenUpgraded on base / arbitrum / optimism (Superfluid wraps, Torex class); arbitrum Pendle SY Redeem (users) and dForce Redeem (a liquidation); bsc Buyback / Released / Exit / Exchanged emitters (tax tokens and staking products run by users or one keeper `0x80c83995`).
- Not opened (few events, no swap in the sampled transactions): arbitrum Convert `0x3caae25e`, TokensRedeemed `0xda8bdc1f`, TokensSwapped `0x2e3dce01`, Redeem `0x30ccf4bb`; hyperevm Redemption `0xffd2cdd8`, Redeem `0x8c4a354b`; base Exit `0x000000000001cdb5`, Redeem `0x583dcfef`, Exited `0x95ccd35a`.
- Not run: ethereum, elysium; a 7-day window.
