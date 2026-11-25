# Review 2026-11-17 21:57 UTC — promote (cheap-chain trial)

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

Source SHA-256: bot `a157ccd3c5840579bd57e6b2504475d26e18f1baad8bd9b09a85c5ec5a6178c2`; manifest `50698031645e965957486db6d9b3a2e34f42d78921238442a8655cdbe907d91b`; executor source `595dec6ced439426a7f9a46462828e74dbc56192da2e617fb9568a9c59cf3d36`.

# Review 2026-11-17 10:54 UTC — wait (cheap-chain trial capacity)

Decision: **wait — cheap-chain trial passes technical review; ten trial bots occupy the live cap**. `next_review_at: 2026-11-17T12:30:00Z`. Reviewer run `031fe56d828f46e9b9ff815619758168`.

`manifest-check.py` PASS and `forge build` PASS. Capital is $15, loss/tx is <$1 by the code's signed fee cap plus $0.02 L1 fee allowance, and the Base native wallet remains below the $18 cap. The bot signs only when simulated gross exceeds its signed gas cap, bids at most 50% of gross as priority fee, and uses `eth_estimateGas` with margin. It waits on the mUSDC `LiquidateBorrow` `/logs` feed with timer scans, never a pending transaction. The owner-only Solidity executor takes targets as call arguments, flash borrows USDC, checks Moonwell error codes, reverts unless USDC gain exceeds `minProfit`, and pays the gain to the bot wallet in the same tx. Live code takes `EXECUTOR_ADDR` and the signer's address correctly; paper mode never sends. No setup transaction is needed.

I independently reran `scratch/trial-moonwell-base/proof.py` at Base parent block 57520472 and `selftest.py` against the current artifact and bot code. The guard tx `0x5e467533...4584169` reverted `NoProfit` with owner USDC unchanged. Success `0x98a5f603...d117b4299d` used 1,304,650 gas and paid 2.433237 USDC to the owner; no-debt and nonowner calls reverted. Executor USDC, cbBTC, mcbBTC, WETH, native and checked mUSDC/Morpho/router allowances were zero after success. Bot calldata matched `cast`; the historical paper override simulated the same 2.433237 USDC gain. A current paper full scan found 38 underwater accounts and skipped accounts without supported collateral; natural capture is waived for trials.

Paid entry in the past seven days: public Moonwell liquidation `0x76a90dcdffd1b0cd4f973fc4299f3e3e4921260f193cc720e7fe7cafd3078659` at block 57520473, with 2.433237 USDC gross versus about $0.035 execution gas in the fork reproduction. The README records 67 sender EOAs, four of nine sampled mUSDC captures still short at least 60 seconds before capture, and 0.0009–64 gwei priority tips. Expected relay plus feed use is 71,000 CU/day = $0.0376/day at $0.53 per million CU; relay reads are capped at 80,000 CU/day. Trial rules waive EV and natural capture. `gate status` shows ten live `trial-*` bots, so promotion is held until a slot opens.

Source SHA-256: bot `a157ccd3c5840579bd57e6b2504475d26e18f1baad8bd9b09a85c5ec5a6178c2`; manifest `50698031645e965957486db6d9b3a2e34f42d78921238442a8655cdbe907d91b`; executor source `595dec6ced439426a7f9a46462828e74dbc56192da2e617fb9568a9c59cf3d36`.
