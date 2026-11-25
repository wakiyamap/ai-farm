---
type: method
chains: [optimism, polygon, avalanche, arbitrum, base, hyperevm, bsc, elysium]
protocols: [tracer_perpetual_pools, azusd_geb_fork, hai, defi_money]
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

## Limits

- Only events whose name is in the lists; a reward paid as a plain transfer with no event is invisible. Add names when a new job is found by other means.
- A window of a day misses weekly and epoch jobs. A 7-day pass costs about 7x the calls, and still misses a job that fires a few times a year (the defi_money keepers above).
- Set 2 has no control emitter on optimism, polygon, hyperevm and elysium, so its zero there only says none of those topics was emitted.
- Beefy `StratHarvest` / `ChargedFees` are in set 1 as a control and are filtered from the printout (`infra/beefy-harvest-rewards.md`).
- Left unresolved on bsc: lead 287. Not opened on arbitrum: `GasReimbursed` on `0xa31d9286` and `0x1aab0125`, one `Rewarded` on `0xf65247b6`.
