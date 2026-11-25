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

Source SHA-256: bot `ef37ba08f258131b5a908d509da97002edc8e8ebd575f88415a6fad9dc2b1a01`; manifest `ca98e8d20810bea2d1b9ba3d7f6800286693cc3f9aa1cc392271fd88d93f7bfc`; executor source `0564ff8cb0d45de845592e2d7d4e0ffbe849f2f438a9ad8620f29c535d004789`.

# Review 2026-11-17 09:18 UTC — wait (cheap-chain trial capacity)

Decision: **wait — cheap-chain trial technically passes; ten trial bots occupy the live cap**. `next_review_at: 2026-11-17T11:30:00Z`. Reviewer run `99cd382d51904b98816c9497e673b64f`.

`manifest-check.py` PASS and `forge build` PASS. The owner-only Solidity executor takes comet, collateral and pools as call arguments, borrows through a UniV3 flash swap, buys public Compound v3 reserve collateral, swaps any USDT surplus to the configured USDC, and reverts unless the USDC payout exceeds `minProfit`. It clears the callback counterparty and exact Comet allowance. The live bot uses `EXECUTOR_ADDR` and the signer's address; paper only simulates. It re-reads reserves on feed gaps and 429/503 errors, with a 10-minute safety poll. Its send rule requires simulated gross above the signed gas cap; priority is at most 25% of gross. Capital $10; gas limit comes from `eth_estimateGas` × 1.25, capped at 900,000; signed execution fee cap plus $0.02 L1 allowance is under $0.95 at its ETH price reference. The OP Stack native-wallet cap is $18.

I independently reran `scratch/trial-cv3-buy-optimism/proof.py`: at fork block 159470694 the high-minimum call `0x6f6cd60c...29114c` reverted with owner USDC unchanged, while success `0x6ddc4183...b8b47` used 317,964 gas and paid 116.181202 USDC to the owner. WETH then paid 31.284237 USDC. The cUSDTv3/OP path paid 3.022947 USDC. Each success left checked executor tokens, native balance and allowance at zero; nonowner and exhausted-reserve calls reverted. I reran the bot's `paper_selftest.py`: it found the WBTC and WETH lots, calculated $0.95 fee caps below their gross payout, and emitted two successful `paper_sim` rows. Natural capture is waived for this trial; live paper logs show regular reserve checks and no errors.

Paid-entry evidence in the past seven days: `0x2ec85415...3857` and `0x25d1a267...e754` at public `buyCollateral`, one block after absorb, with gross about $105 and $29 and priority 3.00/1.02 gwei. The README records six residue buyers, 0–1 block capture and 0.03–3.00 gwei priority. Feed plus safety reads are about 10,000 CU/day = $0.0053/day at $0.53 per million CU, below the 100,000-CU trial limit; code caps relay reads at 60,000 CU/day.

`gate status` shows ten live `trial-*` bots, so the policy cap prevents promotion today. Recheck the slot at the next review. Source hashes (SHA-256): bot `ef37ba08f258131b5a908d509da97002edc8e8ebd575f88415a6fad9dc2b1a01`, manifest `ca98e8d20810bea2d1b9ba3d7f6800286693cc3f9aa1cc392271fd88d93f7bfc`, executor source `0564ff8cb0d45de845592e2d7d4e0ffbe849f2f438a9ad8620f29c535d004789`.
