# Review 2026-11-17 21:57 UTC — promote (cheap-chain trial)

Decision: **promote — cheap-chain trial**. `next_review_at: null`. Reviewer run `34931d202bf643759aef873e877ceff4`.

Prior independent technical approval and fork success/guard reproduction stand. Current bot, manifest and named executor source SHA-256 hashes match the reviewed hashes; `manifest-check.py --all` passes. Human decision `2026-11-18-trial-slots-20.md` raises the live trial limit to 20. At the session start, `gate status` showed 10 live `trial-*` bots, $1,041.59 total capital, no freeze. This promotion follows oldest technical approval first. The earlier review records paid entry, loss cap, CU/day, wallet return, and fork evidence.

# Review 2026-11-17 20:25 UTC — wait (cheap-chain trial capacity)

Decision: **wait — prior cheap-chain trial technical approval stands; ten live trial slots are occupied**. `next_review_at: 2026-11-17T22:30:00Z`. Reviewer run `35ea4b72d5d749ce8831417bf672d3a9`.

Bot code, manifest and named Solidity executor source are byte-identical to the hashes in the prior technical approval. `manifest-check.py --all` passes. Only paper state changed since the previous review. `gate status` at 20:22 UTC shows ten live `trial-*` directories and no freeze. This includes `trial-aave-optimism`, whose promotion funded a $15.02 wallet but failed to deploy its executor; it is inactive, still counts toward X and the live trial cap, and was reported to the human. Recheck capacity after operator recovery. No new fork reproduction is needed for unchanged approved source.

# Review 2026-11-17 17:12 UTC — wait (cheap-chain trial capacity)

Decision: **wait — revised cheap-chain trial passes review; ten trial bots occupy the live cap**. `next_review_at: 2026-11-17T19:00:00Z`. Reviewer run `4f7118b6333f4ef9999b9ea8aeca8f55`.

The revision to `bot.py` and `manifest.yaml` adds a cover-size sweep for debt >= $2,000; the Solidity executor is unchanged. The bot simulates each proposed size, estimates gas for the chosen calldata, requires gross above the signed gas cap, then simulates the exact final calldata with `minProfit` set to that cap. Its priority bid remains at most 50% of gross, with signed gas plus the stated L1 allowance below $0.90; the Base wallet is capped at $18. `manifest-check.py` PASS. The owner-only executor still receives all targets as call arguments, flash funds and settles in one tx, sends USDC or native ETH to the wallet, and leaves no approvals.

I reran `scratch/trial-aave-base/proof.py` with the current artifact at parent block 57496521. The `NoProfit` guard `0x3a50ebd9...85803` reverted with owner USDC unchanged; success `0xabeec9bc...03470` used 531,039 gas and paid 1.446070 USDC to the owner; exhausted and nonowner calls reverted. Executor USDC, WETH, native and Pool/Morpho/router allowances were zero. `selftest.py` matched bot calldata with `cast` and simulated the same gain at the historical parent block. Paper logs show near-list scans and confirmed feed events; a natural capture is waived for trials. The 2026-11-17 cover sweep proof supplied by the builder documents a Polygon large-debt case; I checked the revised Base code but did not claim a new Base large-debt capture.

The existing paid public entry remains tx `0x4a88a8ee33ae524bb2dc15c93475a5b53e4c709761d4e32f3e5e7b7ec9e8039b` (block 57496522), $1.446070 gross versus a few cents of fork gas. README census records about 12 public entry contracts, 14 of 16 sampled captures in the flip block, and priority tips 0.05–779 gwei. Estimated relay plus feed cost is 71,000 CU/day = $0.0376/day at $0.53 per million CU; code caps relay reads at 75,000 CU/day. `gate status` at 17:07 UTC shows ten live `trial-*` bots, so the policy cap prevents promotion now.

Source SHA-256: bot `e169de451066d9c1d1c3562043095d7ae4fec4f44ff7b187ef5096109f1adcfa`; manifest `bb51ba52cc95ab1693ada58c0e9ba31f9ca39bdfa30fd77945f28c451ca1734c`; executor source `789fa643bde78118305896b9cea979dacdfd3e4f513cea807b422b99546457af`.

# Review 2026-11-17 15:35 UTC — wait (cheap-chain trial capacity)

Decision: **wait — prior cheap-chain trial technical approval stands; ten trial bots remain live**. `next_review_at: 2026-11-17T17:00:00Z`. Reviewer run `eb3285a1ce6249b1be5637d795995098`.

Bot code, manifest and named executor source match the SHA-256 hashes in the prior review. Only paper state files changed. `gate status` at 15:33 UTC showed ten live `trial-*` bots, no freeze and no available trial slot. Recheck capacity when a slot opens.

# Review 2026-11-17 12:27 UTC — wait (cheap-chain trial capacity)

Decision: **wait — prior cheap-chain trial technical approval stands; ten trial bots remain live**. `next_review_at: 2026-11-17T14:30:00Z`. Reviewer run `b2721ac28d8e4729967be7e40bb6a2a2`.

Only paper state files changed since the previous review. Bot and manifest modification times predate that review; the previous independent fork success, guard revert and executor checks stand. `gate status` shows ten live `trial-*` bots and no freeze, so no capacity is available. Recheck when a trial slot opens.

Source SHA-256: bot `bd9ea8e01a8fbd67fc5158b0766c002cc208def2a689ed13a0b0496eb2959f9c`; manifest `ea7d148a0379e4df35687eea7050ad70d83c1b1959e5c98d80a64a4f423b0d49`; executor source `789fa643bde78118305896b9cea979dacdfd3e4f513cea807b422b99546457af`.

# Review 2026-11-17 10:54 UTC — wait (cheap-chain trial capacity)

Decision: **wait — cheap-chain trial passes technical review; ten trial bots occupy the live cap**. `next_review_at: 2026-11-17T12:30:00Z`. Reviewer run `031fe56d828f46e9b9ff815619758168`.

`manifest-check.py` PASS and `forge build` PASS. Capital is $15, loss/tx is <$1 by the code's signed fee cap plus $0.02 L1 fee allowance, and the Base native wallet remains below the $18 cap. The bot signs only when simulated gross exceeds its signed gas cap, bids at most 50% of gross as priority fee, and uses `eth_estimateGas` with margin. It waits on the Pool `LiquidationCall` `/logs` feed with timer scans, never a pending transaction. The owner-only Solidity executor takes targets as call arguments, flash borrows the cover, reverts unless the debt-token gain exceeds `minProfit`, and pays USDC or unwrapped ETH to the bot wallet in the same tx. Live code takes `EXECUTOR_ADDR` and the signer's address correctly; paper mode never sends. No setup transaction is needed.

I independently reran `scratch/trial-aave-base/proof.py` at Base parent block 57496521 and `selftest.py` against the current artifact and bot code. The guard tx `0x3a50ebd9...f7385803` reverted `NoProfit` with owner USDC unchanged. Success `0xabeec9bc...1003470` used 531,039 gas and paid 1.446070 USDC to the owner; the subsequent exhausted call and nonowner call reverted. Executor USDC, WETH, native and checked Pool/Morpho/router allowances were zero after success. Bot calldata matched `cast`, and the historical paper override simulated the same 1.446070 USDC gain. The paper log has a `LiquidationCall` feed event followed by scans; natural capture is waived for trials.

Paid entry in the past seven days: public Aave liquidation `0x4a88a8ee33ae524bb2dc15c93475a5b53e4c709761d4e32f3e5e7b7ec9e8039b` at block 57496522, with 1.446070 USDC gross versus about $0.013 execution gas in the fork reproduction. The README records about 12 public entry contracts, 14 of 16 sampled captures in the flip block, and 0.05–779 gwei priority tips. Expected relay plus feed use is 71,000 CU/day = $0.0376/day at $0.53 per million CU; relay reads are capped at 75,000 CU/day. Trial rules waive EV and natural capture. `gate status` shows ten live `trial-*` bots, so promotion is held until a slot opens.

Source SHA-256: bot `bd9ea8e01a8fbd67fc5158b0766c002cc208def2a689ed13a0b0496eb2959f9c`; manifest `ea7d148a0379e4df35687eea7050ad70d83c1b1959e5c98d80a64a4f423b0d49`; executor source `789fa643bde78118305896b9cea979dacdfd3e4f513cea807b422b99546457af`.
