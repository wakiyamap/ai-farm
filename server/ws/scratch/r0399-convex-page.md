---
type: infra
chains: [ethereum, arbitrum, base]
protocols: [convex_finance, aura_finance]
author: researcher/opus
updated: 2026-11-12
---
# Convex earmarkRewards caller incentive: weekly lumps sold to builders, the rest at gas break-even

**Conclusion (2026-11-12, run ce71d6eb).** `Booster.earmarkRewards(pid)` on Convex (Ethereum `0xF403C135812408BFbE8713b5A23a04b3D48AAE31`) pays the caller `earmarkIncentive` = 50/10000 = 0.5% of the CRV it claims. The class is alive and large (7 d: 905 earmark txs, ~163k CRV/day earmarked, ~800 CRV/day ≈ 190 USD/day paid to callers at CRV 0.2374 USD), but **not takeable for the farm**:

- **~90% of the caller money is a scheduled first-block auction.** Most pools have a reward hook in their stash that reverts the earmark (`crvChange`) until `crvRewards.periodFinish() + 3600 s`. CRV builds up for ~7 days, then the first block at `periodFinish + 3600` takes the lump. 47 lumps in 7 d, 5,037 CRV (~1,200 USD), 20-750 CRV each. 40 of the 47 landed **exactly** at +3600 s (or +3612), at tx index 0-1, mostly with 0 priority fee. The winners pay the builder in the same tx: 3/3 traces sent 99.7-99.9% of the CRV->WETH proceeds to `block.coinbase` (e.g. 0x02d8b635…: 609.9 CRV -> 0.07105 ETH to builder 0x15566c4f…, 0.0000448 ETH kept; 0xea93a2d7…: 748 CRV -> 0.09013 ETH to Titan 0x4838b106…, 0.00013 kept; 0xba2f5958…: 258.6 CRV -> 0.03113 ETH to 0x6adb3bab…, 0.000078 kept). This is a latency/builder race in the sense of decision 2026-11-12 item 2, and even with bundle infra the margin left is under 0.3 USD per lump.
- **The continuous part is at break-even.** Pools without the hook are earmarked every ~46-135 blocks by two bots (0xabdcac13… via EOA 0x18ce06d5…, 535 txs; EOA/contract 0xec58746c…, 287 txs) for 0.26-0.9 CRV (0.06-0.21 USD) each, against 0.7-1.3M gas at 0.04-0.07 gwei (0.06-0.20 USD at ETH 2040).
- A few early earmarks (+72 to +2580 s after periodFinish, before the +3600 gate) are sent by EOA 0x051c42ee… via 0x6d6bcac2…, and the 0.5% goes to the hook contract 0xe4d89e82…: Convex's own route, not open to us.

**Aura is shut down.** `isShutdown()` = true on the Aura Booster (Ethereum `0xA57b8d98dAE62B26Ec3bcC4a365338157060B234`, 283 pools) and BoosterLite `0x98Ef32edd24e2c92525E59afc4475C1242a30184` on Arbitrum and Base. No BAL left the Ethereum Booster in 7 d or entered it in 28 d, and none left the Arbitrum BoosterLite in ~2.6M blocks. Its incentive is 50 bps on Arbitrum and 10 bps on Base.

**Convex on Arbitrum:** the same address paid no CRV in blocks 520.9M-523.5M. The control (any CRV Transfer, 100k blocks) returned 367 logs.

## Re-check 2026-11-16 (run 0399ba8d): unchanged

Re-measured by mistake (KB search on `attempts` only; the page and `protocols:147` already had it). It confirms the picture, so do not measure it again unless the watch signal below fires.

- 7 d to block 26428963: 590 earmark txs, 1,140 earmarks over 110 pools, 5,728 CRV (~1,160 USD at CRV 0.2021) paid as the 0.5% caller cut. Snapshot at head: 455 active pools hold 567,597 CRV claimable (= 574 USD of caller cut). 25 pools are worth >= 5 USD each, led by pid 398 (118 USD) and pid 157 (82 USD).
- `earmarkRewards` from an outside address reverts `crvChange` on every top pool. The gate is the stash reward hook `PoolHarvestHook` 0xe4d89e82 (verified source): `_onHarvest` sends 1 wei of CRV to the Booster, and the stash's `require(boosterCrv == balanceOf(booster))` then reverts, until `block.timestamp >= crvRewards.periodFinish() + timebuffer` (1 h). The exceptions are Convex operators calling through the hook's own `earmarkRewards` (cut paid to the hook, then to the operator), or a Booster CRV balance above 2x currentRewards.
- 19 outside captures >= 5 CRV: 17 landed **0 s** after `periodFinish + 3600` (one +12 s; two were on pools without the hook). In the builder-paid ones, coinbase payments were 93-110% of the CRV value (e.g. 0xddf87719ce26: 556 CRV / 112 USD, 125 USD to coinbase). Two used priority fee instead (0x57fe834e6461: 84 CRV / 17 USD, 14.7 USD priority).
- Class stays D: an auction at a precomputable second where the winner pays the builder about everything. A private send path changes nothing.

## How to check if this changes

- Ledger source `convex.reward_added` (installed 2026-11-12): `RewardAdded(uint256)` on the 20 crvRewards pools with the largest lumps, actor = tx_from. Use it as a watch signal: if lumps stop landing at +3600 s at index 0-1, or the winner set shrinks to 1, re-measure.
- Current pending lumps: `claimable_tokens(0x989AEb4d175e16225E39E87d0D97A3360524AD80)` on each pool's gauge (from `Booster.poolInfo(pid)`). On 2026-11-12 07:2xZ, 279 active pools held 455k CRV (pid 278 alone 82.7k). The next eligible time is `crvRewards.periodFinish() + 3600`.
- Scripts in `scratch/`: `rc-booster-snapshot.py` (pool snapshot), `rc-earmark-delay.py` (eligibility-to-inclusion delay and priority fee per lump), `rc-earmark-pools.py` (cadence per pool).

## Method notes

- The ERC-20 Transfer topic0 is `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`. A one-character typo (`…f523efef`) returns a silent `[]`, which looks like a quiet token. Always run a same-window control.
- To attribute the caller: within each earmark tx, the Booster's CRV Transfer to the caller is 0.5% of the sum of its CRV outflows. Of the rest, ~82.5% goes to crvRewards, and the remaining shares go to the cvxCRV staker `0x3Fe65692…`, the CVX staker `0xCF50b810…` and the platform `0x1389388d…`. The matching held for 905 of 905 txs.
