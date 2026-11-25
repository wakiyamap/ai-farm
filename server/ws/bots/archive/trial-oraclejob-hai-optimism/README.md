# trial-oraclejob-hai-optimism

**試行 / TRIAL bot** (decision `decisions/human/2026-11-17-cheap-chain-trials.md` §4, first
of the class): cheap-chain live trial — the timing race rule, EV/day floor and
paper-capture requirements are waived; win rate is measured live. X/n/L/S and the
executor rules (one tx, revert unless the balance ends higher) all apply.

## Mechanism

HAI (Reflexer fork on OP Mainnet) pays **0.05 HAI (~0.0617 USD)** to anyone calling
`OracleJob.workUpdateCollateralPrice(bytes32 cType)` once per collateral item per
3600 s window. 15 items are actively kept = 360 rewards/day ≈ 22.2 USD/day
(attempts:1439). The reward is paid by the StabilityFeeTreasury as **SAFEEngine
internal coins** credited to `msg.sender` (`pullFunds`, Job.sol `reward()` modifier),
so the executor converts: `CoinJoin.exit` → HAI ERC-20 → UniV3 HAI/WETH fee-3000 pool
(HAI = token0) → WETH → ETH, all in one tx, reverting unless the ETH received ≥
`minProfit`. A lost race costs gas only.

## Who earns it now (last 7 d, attempts:1439 + this run)

5 keeper addresses split 2520 rewards: `0xc9dfc714…` 347/705 in a 2 d window, then
`0x82c1ff92…` 182, `0xa88e2855…` 151, `0x9ab1daea…` 13, `0x2d4fcc9d…` 12. Items are
poked in batch txs at per-item hourly phases (observed 16:30:55Z batch
`0xe57a0389…`, an earlier phase at :04:33); every observed gap is exactly 3600 s —
the items are taken in the first blocks of their windows. Winner priority fees
0.0001–0.109 gwei (0.008–0.04 USD per tx); winner txs cost 0.0398–0.102 USD all-in
on ~217–512k gas. That is why this is a trial: it is a first-block race measured in
win rate, not a counted EV.

First live datapoint of the class (sibling `trial-updaterate-hai-optimism`, rate item,
2026-11-16 19:04Z): taker `0x9ab1daea…` landed in the block with ts = due (index 4,
priority 0.0975 gwei, 266,829 gas); our tx was sent 1.0 s before due, the signer took
1.25 s, it landed one block (2 s) later and reverted for 37,395 gas = 3.8e-7 ETH
(0.0007 USD). So a lost attempt costs ~0.001 USD, and the send must leave ~2.4 s
before due to reach the sequencer while the due block is being built.

## What the bot does (timer, rewritten 2026-11-16 run 4886c647 after review 18:57Z)

No polling of `shouldUpdate()`. At start (and hourly) it reads each item's
DelayedOracle (`OracleRelayer.cParams(cType)` word 0; a zero or short answer is
retried and never cached), its `lastUpdateTime()` and `updateDelay()` (3600 s), so
every item's next window `due = lastUpdateTime + updateDelay` is known in advance.
Items due within 3 s of each other form one window (9 windows/hour on 2026-11-16:
five singles, `HAIAERO+MSETH`, `OP+RETH+TBTC+VELO+WETH`, …); the bot sends **one**
executor call per window for one item of the cluster, rotating. Items overdue > 2 h
(`YV-VELO-ALETH-WETH`, not updated since 2026-09, `updateResult()` invalid) are skipped.

Per window: 15 s before due it quotes the reward on the pool (`slot0`), computes
priority fee = min(0.03 gwei, 40% of gross / 369k gas), maxFee = min(0.06 gwei,
2 × base + prio), gas cap = 500k × maxFee, and requires gross > cap + L1 estimate
(5e-8 ETH); `minProfit` = cap + L1 estimate + 1 is passed to the executor, so the
on-chain guard enforces the same condition. It simulates the whole path at head with
the block time overridden to `due` (paper: code override of the fork deployment;
live: `from` = signer `my_address()["address"]`, `to` = `EXECUTOR_ADDR`), sleeps to
`due − lead` (lead 2.4 s, self-adjusting ±0.3 s in 1.6–3.4 s from where the tx
landed) and sends once. Then it logs `receipt` (status, block, gasUsed, fee) and a
`window_result` line: win / lose, the taker's tx, address, block, index, priority fee
and `our_block_minus_taker_block`. A window nobody took is retried once as a "late"
window (simulate at head, send at once), then backed off 10 min.

## Addresses (verified this run, run 4591e288: blockscout ABI/source + eth_calls)

OracleJob `0xF4F18205D8D46638489865e42c0a71a3d4F9FC22` (rewardAmount() = 0.05e18),
StabilityFeeTreasury `0xE9E54c55d41D6622933F9F736e0c55484b3c4f6f`, CoinJoin
`0x30Ce72230A47A0967B7e52A1bAE0178DbD7c6eA3` (`SFT.coinJoin()`), SAFEEngine
`0x9Ff826860689483181C5FAc9628fd2F70275A700`, OracleRelayer
`0x6270403b908505f02da05be5c1956abb59fdb3a6` (`JOB.oracleRelayer()`), HAI
`0x10398AbC267496E49106B07dd6BE13364D10dC71`, UniV3 pool HAI/WETH f3000
`0x146b020399769339509c98B7B353d19130C150EC` (fee() = 3000, token0 = HAI; 24.5k USD
liquidity vs a 0.06 USD sell), WETH `0x4200000000000000000000000000000000000006`.

## Fork proof (one lease, script in manifest `fork_evidence`)

Current proof `scratch/fix-oraclejob-31ba/proof5.py` (run 31babb54, after review
2026-11-16 20:31Z): the executor now calls `SAFEEngine.denySAFEModification(CoinJoin)`
right after `CoinJoin.exit` and requires `safeRights(executor, CoinJoin) == 0` inside
`act()`, so no permission outlives the transaction. Reset 159623936, fresh non-anvil
bot wallet, the bot's real `minProfit`: success `0x9810bee7…` (block 159623939, gas
341,269) wallet delta +23,464,645,175,564 wei net of gas, executor HAI / WETH / ETH /
SAFEEngine coinBalance all 0 and `safeRights` 0 afterwards; reverts `0xc8da21c8…`
(already updated, 136,321 gas) and `0x84f1d25a…` (NoProfit guard, 412,027 gas), both
fee-only deltas with `safeRights` 0. Superseded proofs of the previous executor
(which left the permission set): `scratch/fix-oraclejob-4886/proof4.py` (run 4886c647):
success `0x6254254c…` wallet delta
+22,988,222,375,564 wei net of gas; reverts `0xc7675ac3…` (already updated, 116,418
gas) and `0x3f7149fa…` (NoProfit guard), both fee-only deltas. Earlier proof
(`proof2.py`, anvil account 0 as the bot, whose balance delta does not show the payment):
Reset 159623936 + time-align to ts 1794846655 (the last observed poke block):
success `0xf34b7d6d…` (status 1, gas 368,872, simulated profit 33,741,211,169,416
wei = 0.0616 USD, traced wallet payment of that value, executor left at zero);
nothing-left revert `0xb32c8b94…` and minProfit guard revert `0xfaa62d34…`, both
status 0 with gas-only wallet deltas.

## Read cost

~73k CU/day ≈ **0.039 USD** at 1M CU = 0.53 USD, under the 100k CU/day trial cap:
216 windows/day × ~216 CU (slot0 26 + block 16 + sim 26 + taker getLogs 75 +
receipt 15 + block 16 + cluster re-read ~42) = 47k; hourly full schedule re-read
15 × 24 × 26 = 9.4k; 10-min safety re-read of the next target ≤ 3.7k (rarely
fires, windows are < 10 min apart); live receipt polling ~61 CU × 216 = 13k.
No feed subscription, no per-block or per-minute polling.

## Risks / notes

- A win nets ~0.043 USD (fork, proof5.py: wallet +2.3465e-5 ETH after 341,269 gas at
  0.0301 gwei); a lost attempt reverts for 136,321 gas (fork) ≈ 4.1e-6 ETH ≈ 0.0075
  USD at the same price, so the trial is net positive above a ~15% win rate; 216
  sends/day all lost = ~1.6 USD/day, so the 20 USD budget covers the 7-day trial
  even at a 0% win rate. Incumbents bid up to ~0.1 gwei priority; a
  0.03 gwei bid loses same-block ordering against those and wins only where they
  bid low or arrive a block late — that share is what the trial measures.
- OP L1 data fee (~0.00001 USD/tx measured) is outside the signed cap; the native
  wallet balance is the enforceable worst case on OP-stack chains.
- If HAI depegs the 0.05 HAI exit value moves with it (`minProfit` reverts protect).
- The 20-item `collateralList()` has 5 more items nobody keeps (LUSD-A, LINK, WBTC,
  ALETH + APXETH class); their feeds are likely stale, so the bot sticks to the 15
  actively-kept cTypes and skips any item overdue by more than 2 h.
