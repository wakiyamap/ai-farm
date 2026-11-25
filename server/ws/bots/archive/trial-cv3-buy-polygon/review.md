# Review 2026-11-17 21:56 UTC — promote (cheap-chain trial)

Decision: **promote — cheap-chain trial**. `next_review_at: null`. Reviewer run `34931d202bf643759aef873e877ceff4`.

Prior independent technical approval and fork success/guard reproduction stand. Current bot, manifest and named executor source SHA-256 hashes match the reviewed hashes; `manifest-check.py --all` passes. Human decision `2026-11-18-trial-slots-20.md` raises the live trial limit to 20. At the session start, `gate status` showed 10 live `trial-*` bots, $1,041.59 total capital, no freeze. This promotion follows oldest technical approval first. The earlier review records paid entry, loss cap, CU/day, wallet return, and fork evidence.

# Review 2026-11-17 20:25 UTC — wait (cheap-chain trial capacity)

Decision: **wait — prior cheap-chain trial technical approval stands; ten live trial slots are occupied**. `next_review_at: 2026-11-17T22:30:00Z`. Reviewer run `35ea4b72d5d749ce8831417bf672d3a9`.

Bot code, manifest and named Solidity executor source are byte-identical to the hashes in the prior technical approval. `manifest-check.py --all` passes. Only paper state changed since the previous review. `gate status` at 20:22 UTC shows ten live `trial-*` directories and no freeze. This includes `trial-aave-optimism`, whose promotion funded a $15.02 wallet but failed to deploy its executor; it is inactive, still counts toward X and the live trial cap, and was reported to the human. Recheck capacity after operator recovery. No new fork reproduction is needed for unchanged approved source.

# Review 2026-11-17 17:10 UTC — wait (cheap-chain trial capacity)

Decision: **wait — prior cheap-chain trial technical approval stands; ten trial bots remain live**. `next_review_at: 2026-11-17T19:00:00Z`. Reviewer run `4f7118b6333f4ef9999b9ea8aeca8f55`.

Bot code, manifest and named executor source remain byte-identical to the SHA-256 hashes in the previous technical review. Only paper state changed. `gate status` at 17:07 UTC showed ten live `trial-*` bots and no freeze; the human decision `2026-11-17-cheap-chain-trials.md` limits simultaneous live trials to ten. Recheck when a slot opens.

# Review 2026-11-17 15:35 UTC — wait (cheap-chain trial capacity)

Decision: **wait — prior cheap-chain trial technical approval stands; ten trial bots remain live**. `next_review_at: 2026-11-17T17:00:00Z`. Reviewer run `eb3285a1ce6249b1be5637d795995098`.

Bot code, manifest and named executor source match the SHA-256 hashes in the prior review. Only paper state files changed. `gate status` at 15:33 UTC showed ten live `trial-*` bots, no freeze and no available trial slot. Recheck capacity when a slot opens.

# Review 2026-11-17 12:27 UTC — wait (cheap-chain trial capacity)

Decision: **wait — prior cheap-chain trial technical approval stands; ten trial bots remain live**. `next_review_at: 2026-11-17T14:30:00Z`. Reviewer run `b2721ac28d8e4729967be7e40bb6a2a2`.

Only paper state files changed since the previous review. Bot and manifest modification times predate that review; the previous independent fork success, guard revert and executor checks stand. `gate status` shows ten live `trial-*` bots and no freeze, so no capacity is available. Recheck when a trial slot opens.

Source SHA-256: bot `1bab898986c61aa67d699e54ebd8076b96ed3a35c6724a9ff95e0f654e68d35f`; manifest `82c1d2f4f21053e41ad59855df8d4ef25617cdfac063c3ec9e67566ea0e0c3d4`; executor source `2a991ba246825afacdf7ab0578bb27c07b645e88d6b556d4384dc7fbcff81c39`.

# Review 2026-11-17 09:18 UTC — wait (cheap-chain trial capacity)

Decision: **wait — cheap-chain trial technically passes; ten trial bots occupy the live cap**. `next_review_at: 2026-11-17T11:30:00Z`. Reviewer run `99cd382d51904b98816c9497e673b64f`.

`manifest-check.py` PASS and `forge build` PASS. The owner-only Solidity executor takes the comet, collateral and both pools per call, flash swaps the collateral, buys public Compound v3 reserves, converts USDC.e surplus through the USDC.e/USDC pool and pays configured native USDC to the bot wallet. It reverts unless the payout exceeds `minProfit`, clears the callback counterparty and exact Comet allowance, and holds no proceeds. Live code uses `EXECUTOR_ADDR` and the signer dict; paper does not send. Feed gaps and 429/503 cause a reserve reread; a 10-minute safety poll remains. Capital $10. A send needs simulated gross above its fee cap; gas limit is `eth_estimateGas` × 1.25, at most 2,000,000, priority bid at most 25% of gross and total signed gas cap below $0.95 at its POL price reference.

I independently reran `scratch/trial-cv3-buy-polygon/proof.py` at fork block 97332763: high-minimum `0x3c90de54...236449` reverted with owner USDC unchanged; `0x28ae9a98...bd302` used 664,191 gas and paid 102.954515 USDC to the owner. A second WPOL lot paid 11.697405 USDC. At block 97334218, a 50% WBTC lot paid 128.178912 USDC after the full lot simulation reverted, and WETH paid 139.121373 USDC. Each success left checked USDC, USDC.e, collateral, native and Comet allowance at zero; nonowner and exhausted-reserve calls reverted. I reran the bot's `paper_selftest.py` without its two bot-directory copy/chmod lines: its own `check()` found WETH and WPOL, computed $0.95 gas caps below gross and emitted two `paper_sim` successes. Natural capture is waived for this trial; normal paper logs show reserve checks.

Paid-entry evidence in the last seven days includes public `buyCollateral` tx `0x4be4f088...25b3` (124.26 USDC.e gross, 1 block after absorb) and `0x6aa6a3d3...19d2` (156.8 WPOL gross). The README records six residue buyers, 0–2 block capture, and priority from 35 to 2,637,034 gwei. Feed plus safety reads are about 10,000 CU/day = $0.0053/day at $0.53 per million CU, below the 100,000-CU trial limit; code caps relay reads at 60,000 CU/day.

`gate status` shows ten live `trial-*` bots, so the policy cap prevents promotion today. Recheck the slot at the next review. Source hashes (SHA-256): bot `1bab898986c61aa67d699e54ebd8076b96ed3a35c6724a9ff95e0f654e68d35f`, manifest `82c1d2f4f21053e41ad59855df8d4ef25617cdfac063c3ec9e67566ea0e0c3d4`, executor source `2a991ba246825afacdf7ab0578bb27c07b645e88d6b556d4384dc7fbcff81c39`.
