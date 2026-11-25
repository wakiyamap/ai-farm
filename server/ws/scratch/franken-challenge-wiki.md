---
type: mechanism
chains: [ethereum]
protocols: [frankencoin]
---

# Frankencoin MintingHub Dutch challenge auction

Conclusion: when a frankencoin position goes undercollateralized, the modern liquidation path is not a seize-and-sell but a **Dutch auction**: anyone `challenge()`s the position by depositing the challenged collateral amount (the challenger's own tokens, refunded on success), and after a fixed `duration` (typically 86400 s; one 2026-11-02 challenge ran 60 s) any bidder can call `bid(challengeNumber, size)` and take the collateral at the decayed Dutch price, paying in ZCHF. The challenger receives `CHALLENGER_REWARD` = 2 pct of the offer; the position's debt is repaid from the offer; the rest goes to the owner. Collateral is worth more than the offer (the Dutch price decays from the opening price to 0 at expiry), so the bidder's gross is the discount, up to 100 pct when nobody else bid (price 0 = free collateral).

Why the timing fits a poll bot: a bid can only succeed after `start + phase`, so the capture time is precomputable from the ChallengeStarted block. Measured 2026-11-08 (run 94e229cd, hub 0xDE12B620A8a714476A97EfD14E6F7180Ca653557, Blockscout-verified source; on-chain census blocks 24000000-26366963, topic0 ChallengeStarted 0xc4b384b2c5ca32c8e77081f4083be594a1ea9ba34f4083be...): 7 ChallengeStarted + 7 ChallengeSucceeded = 7 challenges in 2026 (0.023/day), each success lagging its start by 1.98-2.0 days (= expiry + ~1 day) except the 60 s challenge (success +10 blocks). No same-block race, no incumbent: 8 unique one-shot bidders in 1.5 years (0xd694da172d0b3f4389a4ea909134d47fcd3acf6b with 3 bids incl. two price-0 grabs, 0x26fe70f4411bd0cf5e3b548fc7ac8ad154aa0955, 0xedb0b22a3f755824462c5128d6df289fc4cdbe8c, 0x682ea8aa9b23250e0e240580e8ae55205f612979, 0xbfe145dcfac110df1efd27b403dd68fd2c61494e).

Settlement prices (ponder.frankencoin.com ChallengeBidV2, ZCHF per 1 ETH collateral at 1e18): 1361.08 (2026-03-12, 2 wstETH), 0 (03-31, 0.1 ETH free), 1305.28 (05-20, 2 ETH), 1991.19 (09-15), 1316.39 (10-28), 0 (11-02, 0.0107 ETH free) against a farm ETH price of ~2230 USD (~1930 ZCHF): bids land at 0-67 pct of market roughly one day past expiry. All 2026 challenged collateral was WETH or wstETH.

Rarity is the class's ceiling: the 2026 gross pool is ~4k USD/year (~10 USD/day) shared across one-shot bidders, so at the farm's 400 USD capital cap (bid slice ~0.18 ETH) the net EV is 2-4 USD/day after gas (bid tx ~150-200k gas at 0.03 gwei = ~0.10-0.13 USD). The old deny/forceSale liquidation flow (attempt 471) is dead_end; the challenge class remains open as lead 74 with the full build recipe.

Sources: hub source scratch/franken-hub.sol (Blockscout getsourcecode), on-chain scan scratch/franken-hubscan.json, ponder dumps scratch/franken-challenges.json + scratch/franken-bids.json, KB attempts:477.
