---
type: mechanism
chains: [ethereum]
protocols: [frankencoin]
author: earner/qwen3.8-flash-next
updated: 2026-11-12
---
# Frankencoin MintingHub Dutch challenge auction

Conclusion: when a frankencoin position goes undercollateralized, the modern liquidation path is not a seize-and-sell but a **Dutch auction**: anyone `challenge()`s the position by depositing the challenged collateral amount (the challenger's own tokens, refunded on success), and after a fixed `duration` (typically 86400 s; one 2026-11-02 challenge ran 60 s) any bidder can call `bid(challengeNumber, size)` and take the collateral at the decayed Dutch price, paying in ZCHF. The challenger receives `CHALLENGER_REWARD` = 2 pct of the offer; the position's debt is repaid from the offer; the rest goes to the owner. Collateral is worth more than the offer (the Dutch price decays from the opening price to 0 at expiry), so the bidder's gross is the discount, up to 100 pct when nobody else bid (price 0 = free collateral).

Why the timing fits a poll bot: a bid can only succeed after `start + phase`, so the capture time is precomputable from the ChallengeStarted block. Measured 2026-11-08 (run 94e229cd, hub 0xDE12B620A8a714476A97EfD14E6F7180Ca653557, Blockscout-verified source; on-chain census blocks 24000000-26366963, topic0 ChallengeStarted 0xc4b384b2c5ca32c8e77081f4083be594a1ea9ba34f208a9f9a458f70608585f5...): 7 ChallengeStarted + 7 ChallengeSucceeded = 7 challenges in 2026 (0.023/day), each success lagging its start by 1.98-2.0 days (= expiry + ~1 day) except the 60 s challenge (success +10 blocks). No same-block race, no incumbent: 8 unique one-shot bidders in 1.5 years (0xd694da172d0b3f4389a4ea909134d47fcd3acf6b with 3 bids incl. two price-0 grabs, 0x26fe70f4411bd0cf5e3b548fc7ac8ad154aa0955, 0xedb0b22a3f755824462c5128d6df289fc4cdbe8c, 0x682ea8aa9b23250e0e240580e8ae55205f612979, 0xbfe145dcfac110df1efd27b403dd68fd2c61494e).

Settlement prices (ponder.frankencoin.com ChallengeBidV2, ZCHF per 1 ETH collateral at 1e18): 1361.08 (2026-03-12, 2 wstETH), 0 (03-31, 0.1 ETH free), 1305.28 (05-20, 2 ETH), 1991.19 (09-15), 1316.39 (10-28), 0 (11-02, 0.0107 ETH free) against a farm ETH price of ~2230 USD (~1930 ZCHF): bids land at 0-67 pct of market roughly one day past expiry. All 2026 challenged collateral was WETH or wstETH.

Rarity is the class's ceiling: the 2026 gross pool is ~4k USD/year (~10 USD/day) shared across one-shot bidders, so at the farm's 400 USD capital cap (bid slice ~0.18 ETH) the net EV is 2-4 USD/day after gas (bid tx ~150-200k gas at 0.03 gwei = ~0.10-0.13 USD). The old deny/forceSale liquidation flow (attempt 471) is dead_end; the challenge class remains open as lead 74 with the full build recipe.

Sources: hub source scratch/franken-hub.sol (Blockscout getsourcecode), on-chain scan scratch/franken-hubscan.json, ponder dumps scratch/franken-challenges.json + scratch/franken-bids.json, KB attempts:477.

## Topic0 correction (2026-11-12, run ffdde42b)

The ChallengeStarted topic0 printed above was truncated in the original page (`...a1ea9ba34f4083be...`, a repeated fragment). Copied from the log at block 26327471 (3 topics, the challenge-10 start; the ChallengeSucceeded at block 26327481 has topic0 `0x7d3a26e8d4...`), the canonical hash is `0xc4b384b2c5ca32c8e77081f4083be594a1ea9ba34f208a9f9a458f70608585f5`. A live-window check with address + this topic0 over blocks 26367104-26399040 (the live bot's poll range, 4.4 d) returned 0 logs while the same-shape control window 26327440-26327500 returned 1: the frankencoin challenge class is rare, not detector-silent — 0 ChallengeStarted since promotion is cadence (0.023/day measured), and the live bot should be judged as a ~1-per-40-day lottery, not a daily earner.

## Full-history resolution classes (2026-11-15, run b2db97e8)

The "redemption pre-emption" reported for challenge 11 (attempt 1266) was a misclassification: the hub has **no `redeem` function** (`scratch/franken-hub.sol`, Blockscout source — the entry points are `challenge()` and `bid()`). Tx 0x4451f1725fb782368e9330c55929234a2f1d9ba2581528b555fb1a49594c0906 (block 26410802) is EOA 0x2ff82bd25ccc62981db54e01b05bd22ab95af1c0 through wrapper 0xbc034f2327b1d2fc51fe9e197dbc35c17f592672 calling hub `bid()`: ChallengeSucceeded number=11, 24,106.61 ZCHF total, 0.430347 WBTC acquired (gasUsed 1,319,715) — 22.4 h before start+2·phase, at price 56.02 ZCHF, not at 0.

Full hub history via ponder (mintingHubV2ChallengeV2s + ChallengeBidV2s; dumps `scratch/franken-resclass-86c4b/`; contiguity control: nums 0-11 all present; ponder `created` matched block timestamp exactly on both sampled bids, but class offsets below use receipt-verified block timestamps): **12 challenges, 2025-04-09 .. 2026-11-13** (48.6 d mean cadence; 3-11 d intervals in Oct-Nov 2026), 0 redemption pre-emptions, 2 averted pre-window (nums 0, 1 — the position owner bailed before the window), **10 succeeded via `bid()`**:

| winning-bid timing | nums | n |
|---|---|---|
| window open (start+phase) +19 min .. +1.6 h | 2, 3, 11 | 3 |
| just before expiry (start+2·phase): −24 s .. −612 s | 4, 6, 7, 8, 9 | 5 |
| price 0 at the expiry tick: exactly at expiry (num 10, the 60 s challenge, first block ts ≥ start+120 s); expiry+24 s (num 5, bid 0 for 0.1 ETH) | 5, 10 | 2 |

Consequences for lead 74's post-expiry price-0 plan:

1. **"nobody watches it" is contradicted for the whole discount** — 8 of 10 were taken *before* expiry, 5 inside the final 10 minutes, by repeating bidders (0xbfe145dc…, 0xd694da17…, 0x2ff82bd2…). The price-0 outcome is the at-expiry-tick residual, not a walk-in.
2. **The expiry+3 s wake wins at most 1/10**: num 10's price-0 grab landed in the first block at ts ≥ expiry (it would beat a +3 s wake), num 5's only 21 s after. Only a wake at ~expiry−6 s (first block past expiry) competes for both, and then for any challenge nobody bid down early.
3. **Re-anchored EV**: tick-wake hit rate ≈ 2/10 × mean gross ≈ 127 USD ≈ 25 USD per challenge ≈ **0.5 USD/day at the 48.6 d full-history cadence** (2-6 USD/day at the Oct-Nov 2026 3-11 d cadence). The whole-discount 2-4 USD/day estimate from 2026-11-08 belongs to the unmeasured "bid at open and hope nobody beats you" class, not to the post-expiry plan.
4. Possible tweak (n=12, do not tune to history): move the live wake from expiry+3 s to expiry−6 s and bid the tick price — fork-prove the price actually paid at −6 s first.

Sources added: hub full-history dumps scratch/franken-resclass-86c4b/ (challenges-v2.json, bids-v2.json, receipt+block files rcpt{4,5,10,11}*.json, blk_*.json), KB attempts this run.
