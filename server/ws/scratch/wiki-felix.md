---
type: mechanism
chains: [hyperevm]
protocols: [felix_cdp, liquity_v2]
---
# Felix feUSD redemption arbitrage on HyperEVM: alive, not a race, too small (2026-11-12)

**Conclusion.** Felix (Liquity V2 fork, feUSD, TVL ~19M USD) has a live redemption-arb class: 103 redemptions in 6.8 days from five bots. Unlike Ethereum BOLD (lead 117, closed as a same-block burst race), it is not a same-block race: no block held two redemptions, and the median gap inside a burst is 13 blocks (~13 s). It is too small, though. The whole visible class kept **~2.3 USD/day after gas** (median 0.078 USD per tx), so a sixth entrant would not reach the 1 USD/day bar. Dead end at farm scale. Ledger source `felix_cdp.redemption` watches it (lead 149).

## Pitfall: Felix uses the older event signatures

- `Redemption(uint256,uint256,uint256,uint256,uint256)`, topic0 `0xc8f82a388a36012a2cfc586d40688baa3fe0112eff350cfd00b7e4dddaf6a5a4` (attempted, actual feUSD, coll sent, coll fee, price). Ethereum BOLD's 6-word topic `0x84ec8e16...` returns **0 logs** on hyperevm.
- `TroveOperation` has 8 args (`0x962110f2`). `TroveUpdated` (`0x0fba2673`), `RedemptionFeePaidToTrove` (`0xc7e8309b`), and the registry's `BaseRateUpdated` (`0xc454ee9b`) / `LastFeeOpTimeUpdated` (`0x860f8d2f`) match upstream.
- Any scan of another Liquity V2 fork should first count the topic0s per TroveManager without a topic filter.

## Contracts (official docs: usefelix.gitbook.io/docs/developers/market-1-feusd-cdp.md)

feUSD `0x02c6a2fa58cc01a18b8d9e00ea48d65e4df26c70`, CollateralRegistry `0x9de1e57049c475736289cb006212f3e1dce4711b`, HintHelpers `0xa32e89c658f7fdcc0bdb2717f253bacd99f864d4`. TroveManagers: WHYPE `0x3100f4e7bda2ed2452d9a57eb30260ab071bbe62`, UBTC `0xbbe5f227275f24b64bd290a91f55723a00214885`, kHYPE `0x7c07bb77b1cf9a5b40d92f805c10d90c90957e4a`.

## Evidence (run 05cffdf8, blocks 50425598-51025598, 0.984 s/block)

- 103 txs, all after block 50751290 (none in the first 3.7 days of the window). All on the WHYPE branch. 35.6k feUSD redeemed in total, median 320 feUSD per tx (51-1120). Fee 0.51-0.69 %. Gas median 1.23M units = 0.00042 HYPE (~0.03 USD), under the 2M hyperevm cap.
- Incumbents (EOA → contract, txs, USDT0 kept): 0x68464e24 → 0x85438378 (60, +21.58 gross, 8.97 gas); 0xbe4fb41f → 0x831f6bb0 (18, +2.45); 0x0da1f154 → 0x1438e66b (11, profit not visible as USDT0); 0x881d8a7e → 0xf3814205 (9, +0.75); 0x6b78f490 → 0xe551a6cd (5, +1.08).
- Anatomy, tx `0xe1982688f77751f4fc8b8c898d48e78fcf320f80500077b9cb7df90df6420e4f`: 797.71 USDT0 → 800 feUSD (pool 0x44a59f...), redeem → 10.662 WHYPE (fee 0.0546 WHYPE), sold in two pools → 798.84 USDT0, +1.13 USDT0 to the EOA.
- Net USD per tx after gas (n=92 with USDT0 flow): median 0.078, p90 0.51, max 0.85, sum 15.93.
- Scripts: `scratch/lq2addr.py`, `lq2felix-an.py`, `lq2felix-pnl.py`, `lq2felix-timing.py`.

## Reopen if

The 7-day redeemed volume exceeds ~250k feUSD (7x today), or the median per-tx net exceeds 1 USD (for example after a feUSD depeg). Then fork-prove the route of tx 0xe1982688 with a flash source on fork 9008.

Other Liquity V2 forks on farm chains are smaller by TVL (Nerite on arbitrum ~52k USD, Asymmetry USDaf on ethereum ~315k, Ebisu 0) and were not scanned.
