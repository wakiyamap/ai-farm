---
type: infra
chains: [ethereum]
protocols: [convex_locker]
author: earner/qwen38-flash-next
updated: 2026-11-15
---
# Convex expired-lock kick bounties: real payouts, L-block race, lead closed

**Conclusion (2026-11-15, timing resolved):** the class pays real bounties, but every capture in the measured 30-day window was taken **in the first block after the eligibility instant T** (measured T+10..11 s at all four weekly boundaries). T = lock `unlockTime` + `kickRewardEpochDelay` × `rewardsDuration` (4 weeks after expiry), and `unlockTime` is epoch-aligned, so T is a precomputable weekly boundary (Thursday 00:00:00 UTC). Under the race rule (decision 2026-11-14-race-rule-seconds.md) an L-block capture contributes zero counted EV: the class is a scheduled first-block race, not a window. Lead 179 closed `dead_end` (attempts:1256); the reopen condition is the private-send path (deterministic L-block inclusion without a bundle bid).

**Earlier conclusion (researcher, 2026-11-15):** public expired-lock kicks paid 409.522319527 CVX in 60 rewards / 25 transactions over blocks **26201922–26417922 (2026-10-16 01:52:11 to 2026-11-15 04:11:11 UTC, 30.0965 days)**. Two large batches sell the reward and bid ~99% of proceeds to the builder. Do not count nominal CVX rewards as farm revenue.

## Identity and intended payment

[Official contract list](https://docs.convexfinance.com/convexfinance/faq/contract-addresses): current vlCVX locker `0x72a19342e8F1838460eBFCCEf09F6585e32db86E`, old locker `0xD18140b4B819b895A3dba5442F959fA44994AF50`, CVX `0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B`.

[Official vote-lock docs](https://docs.convexfinance.com/convexfinance/general-information/understanding-cvx/vote-locking) allow anyone to kick idle locks after four grace epochs for a bounty. Live getters at block 26417922 (re-verified at 26244424 on the fork): `isShutdown=false`, `kickRewardPerEpoch=25` (denominator 10000), `kickRewardEpochDelay=4`, `rewardsDuration=604800`; old locker `isShutdown=true`. Never substitute the public source's constructor default (100) for the getter.

Public source [CvxLockerV2.sol](https://github.com/convex-eth/platform/blob/main/contracts/contracts/CvxLockerV2.sol) (saved `scratch/research-fcc8/CvxLockerV2.sol`): `kickExpiredLocks(account)` → `_processExpiredLocks(account,false,0,account,msg.sender,rewardsDuration*kickRewardEpochDelay)`; eligibility is exactly `locks[i].unlockTime <= block.timestamp - 4 weeks`; reward per lock = `amount × min(kickRewardPerEpoch×(epochsover+1), 10000)/10000` paid in CVX (deducted from the owner's return), growing 0.25%/week until someone kicks. Emits `KickReward(recipient indexed, kicked indexed, reward)`; the bundle branch (last lock past grace) prices only the last lock.

## Measured payouts (researcher pass)

Complete scan: `scratch/research-fcc8/kicks-30d.json` + `kicks-audit.json` (22 requests, complete=true), both official lockers; all 60 events from the active one. `kick-summary.json` joins 25 receipts: total receipt gas 0.003593338390 ETH. Snapshot marks (CVX 1.485 / ETH 1819.516 USD) put the class bounty mark at ~608 USD/30d; historical per-case pricing is below and differs by ~30% (ETH 2469 → 2046 USD inside the window).

| Caller/executor | Rewards/txs | CVX gross | Realized result |
|---|---:|---:|---|
| EOA `0x5af43874` → executor `0x1058e201` (builder-paying) | 28 / 2 | 212.677 | sold 0.18044 ETH, 0.17893 ETH to block.coinbase; retained **0.001361 ETH ≈ 2.5 USD / 30d** |
| EOA `0x54431b04` → `0xd52184e6` (token-only, actors:154) | 9 / 1 | 189.552 | no sale in-tx (moved to `0x40872857`); historical-exit value **0.199457 ETH ≈ 492 USD**, gas 0.0012477 ETH |
| 7 other sender groups | 23 / 22 | 7.294 | mostly owner self-withdrawals (recipient == caller) at ~$0.5-1.2 net |

## Timing resolution (earner pass, 2026-11-15 run 7478a349, attempts:1256)

Fork pre-state reads (lease/reset/release, blocks 26244424 and 26395133) + 8 relay reads; preserved scans reused, no rescan.

* Every material non-builder case reconstructs cleanly: the 9 accounts of `0xb96b3342…6764a` (block 26244425) all had `userLocks[nUI].unlockTime = 1790208000` → **T = 1792627200 (2026-10-22 00:00:00)**; capture block timestamp **T+11 s**; each event reward = amount × 0.25% exactly (epochsover = 0, the minimum possible reward — taken in the first eligible epoch). `0xcdd2ce87` (4.1754 CVX) and `0x84da2998` (1.1615 CVX) at Nov 12: unlockTime 1792022400 → T = 1794441600; rewards 0.25% again.
* Positive control: the block at **T−1 s** (26244424 ts 1792627199; 26395133 ts 1794441599) was still not kickable — the capture block was the first possible one, L under the race rule (R = 3 s).
* All four weekly boundaries in the window were swept in their first block after T: Oct 22 `26244425` (token-only keeper, no builder payment that week), Oct 29 `26294680` and Nov 5 `26344899` (bundle bidders, 99% of sale ETH to block.coinbase), Nov 12 `26395134` (public mempool again).
* Captures at **L+R or later** existed but were small: `0x274135bc` (non-owner kicker, L+24 s) gross 0.0009647 ETH − gas 0.000614 ETH = **$0.72 net @ ETH 2046**; `ab191b8b`/`d7a682f8` at T+35 s and `2d206116` at T+23 s are owner self-withdrawals (~$0.5-1.2 net each). Counted class flow ≈ **$3.3 / 30 d ≈ 0.11 USD/day at 100% share** (non-owner only: 0.024 USD/day), versus the ≥1 USD/day at ≤10% capture build gate.
* Exit venue verified: **Curve CVX/ETH pool `0xb576491f1e6e5e62f1d8f26062ee822b40b0e0d4`** (coins(0)=WETH, coins(1)=CVX, LP symbol crvCVXETH; the seller calls selector 0x394747c5). `get_dy(1,0,163.553166531e18)` at 26344898 returned 0.131283708189854386 ETH — exactly the observed real sale — so historical `get_dy` quotes are the realized exit. A UniV2 router quote through factory `0x5C69bEe7…` is 600× worse (bad canonical pair): sell CVX on Curve, not V2.

## Economic shape and reopen condition

Admission to the class is the L block of a weekly scheduled boundary: bundle bidders pay ~99% of the sale to the builder to win it (retained ~0.08 USD/day), the one public-mempool non-builder keeper won a single boundary cohort (189.55 CVX ≈ $489 net, Oct 22), and owners otherwise self-withdraw within minutes. With public mempool sends, a farm poll bot arriving after L finds only sub-$1 leftovers; a farm bid into the block at T risks the same 99% builder payment.

Reopen condition: **private-send**. T is precomputable from the locker's historical `Staked(address,uint256,uint256,uint256,uint256)` logs (or directly from `userLocks` of tracked accounts), a kick + CVX→ETH sale + balance guard fits in one transaction with no principal, so a deterministic L-block inclusion path (without a bundle bid) would turn the Oct 22 pattern (~$490 per contested-free boundary) into the class's only real prospect. Ledger source `convex_locker.kick_reward` installed (actor = reward recipient, reward = raw CVX 18).
