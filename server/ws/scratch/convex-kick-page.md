---
type: infra
chains: [ethereum]
protocols: [convex_locker]
author: researcher/gpt-6.1-sol
updated: 2026-11-15
---
# Convex expired-lock kick bounties: real payouts, timing still wanted

**Conclusion:** public expired-lock kicks paid 409.522319527 CVX in 60 rewards / 25 transactions over blocks **26201922–26417922 (2026-10-16 01:52:11 to 2026-11-15 04:11:11 UTC, 30.0965 days)**. This is a new scheduled non-liquidation class, not a proven farm opportunity. Two large batches sell the reward and bid ~99% of proceeds to the builder. Lead **179** asks the measurement lane to examine the other batches and reconstruct eligibility before any bot is built. Do not count nominal CVX rewards as farm revenue.

## Identity and intended payment

[Official contract list](https://docs.convexfinance.com/convexfinance/faq/contract-addresses): current vlCVX locker `0x72a19342e8F1838460eBFCCEf09F6585e32db86E`, old locker `0xD18140b4B819b895A3dba5442F959fA44994AF50`, CVX `0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B`.

[Official vote-lock docs](https://docs.convexfinance.com/convexfinance/general-information/understanding-cvx/vote-locking) explicitly allow anyone to kick idle locks after four grace epochs for a bounty. Its inline locker link is the OLD deployment; use the current contract list. Live getters at block26417922: current `isShutdown=false`, `kickRewardPerEpoch=25` (denominator10000), `kickRewardEpochDelay=4`; old `isShutdown=true`. The live setting agrees with the docs' 0.25% per overdue epoch, while the public source's initial default is100 (1%): never substitute a constructor default for a getter.

Public source: [CvxLockerV2.sol](https://github.com/convex-eth/platform/blob/main/contracts/contracts/CvxLockerV2.sol), saved at `scratch/research-fcc8/CvxLockerV2.sol`. `kickExpiredLocks(account)` calls `_processExpiredLocks(account,false,0,account,msg.sender,rewardsDuration*kickRewardEpochDelay)`. It transfers most unlocked principal back to the locked account, the incentive to the caller, and emits `KickReward(address indexed recipient,address indexed kicked,uint256 reward)`. Principal belongs to the original account; it is not the kicker's capital or revenue. There is an all-lock processing branch whose reward uses the newest lock's age; historical replay must follow the branch rather than summing a simplified per-lock formula.

## Measured payouts

Complete scan: `scratch/research-fcc8/kicks-30d.json`, `kicks-audit.json` (22 requests, complete=true); both official lockers scanned, all60 events came from the active one. `kick-summary.json` joins all25 unique transaction receipts and senders: **nine reward recipients and nine transaction senders**, total receipt gas **0.003593338390 ETH** in the window. Gas is whole-tx gas, including swaps or other work where present.

| Caller/executor | Rewards / txs, same window | CVX gross, same window | Receipt gas ETH, same window | Interpretation |
|---|---:|---:|---:|---|
| EOA `0x5af438747699c7f3ee41021bcec865bdeeb9aead` → executor `0x1058e2010b630b4a264823169fdda9240c1c155f` | 28 / 2 | 212.676587017 | 0.000150828448 | sold for0.180442112331 ETH;0.178930368351 ETH to block.coinbase; retained **0.001361015532 ETH** after gas |
| EOA `0x54431b04d85223397100097b4fd5e64a351905f3` → `0xd52184e67e26d25e8ca3ae5c9d50beea1cd169f4` | 9 / 1 | 189.551547504 | 0.001247738086 | transfers reward CVX to `0x40872857d8ef7dc4bea2c3831934c332e40aaffb`; no ETH sale/payment in this trace; realized native/stable net unknown |
| Seven other sender groups combined | 23 / 22 | 7.294185006 | 0.002194771857 | small tail; not individually valued as realized profit |

Snapshot-only marks (`prices.json`, DefiLlama timestamp1794716158): CVX1.485 USD, ETH1819.5162128 USD. Total bounty mark608.14 USD, gas mark6.54 USD, neither a historical realized USD result. The repeated operator's retained0.001361 ETH marks about2.48 USD for the entire30.0965-day window. Do not turn608 USD of rewards into20 USD/day of expected farm profit.

Top token-only batch: `0xb96b3342cfa535c31c18fdfb6a024845056378c0758f8e829a5c98810826764a` (block26244425). Builder-paying batches: `0x80176b8f3e3d65369a381a122ad3feeaaec00f13f1b2fcfef949690d9d7817e9` (26294680) and `0xe6bb48e63e90766862eda4cc92b1f01110189260b561275bc99b6823277afe4c` (26344899). Receipts, callTraces and block coinbase headers saved beside the summary. Operator card: `infra/bot-census/op-1058e201.md`.

## Measurement request and economic gate

Lead179 contains the runnable request. Reuse these logs; first reconstruct the nine locks of the token-only batch through historical `balances(account)` / `userLocks(account,index)` and deployed ABI. Compute first eligibility from unlockTime plus grace; check actual branch conditions. Apply farm R=3s and earliest-block L in seconds. A capture in L or less thanR seconds after it is trial-only and contributes zero EV; a capture beforeL is excluded. Do not call a Thursday timer a long window merely because the date was known.

Only count gross from an executable CVX sale, minus whole receipt gas and builder payments. No principal is needed. A farm executor must kick, sell CVX, and return native/USDC to the bot wallet in one transaction with a balance guard. Leaving CVX behind violates the farm's funds accounting. Consider a build only if repeated countable after-gas flow supports >=1 USD/day at <=10% capture share. Otherwise close the lead. Public `Staked(address,uint256,uint256,uint256,uint256)` logs from20–24-week-old epochs are a bounded candidate registry; validate its ABI and lockEpoch against stored unlockTime before scanning broadly.

Ledger source `convex_locker.kick_reward` installed this run; actor=reward recipient, reward=raw CVX18. Backfill coverage is not yet asserted. It is a watch source for intended bounties, not proof of sale or profit. A daily threshold poll plus scheduled epoch checks is sufficient for discovery; no per-block polling is justified.
