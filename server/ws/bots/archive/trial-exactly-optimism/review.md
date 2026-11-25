# Review 2026-11-17 21:58 UTC — promote (cheap-chain trial)

Decision: **promote — cheap-chain trial**. `next_review_at: null`. Reviewer run `34931d202bf643759aef873e877ceff4`.

Prior independent technical approval and fork success/guard reproduction stand. Current bot, manifest and named executor source SHA-256 hashes match the reviewed hashes; `manifest-check.py --all` passes. Human decision `2026-11-18-trial-slots-20.md` raises the live trial limit to 20. At the session start, `gate status` showed 10 live `trial-*` bots, $1,041.59 total capital, no freeze. This promotion follows oldest technical approval first. The earlier review records paid entry, loss cap, CU/day, wallet return, and fork evidence.

# Review 2026-11-17 20:25 UTC — wait (cheap-chain trial capacity)

Decision: **wait — prior cheap-chain trial technical approval stands; ten live trial slots are occupied**. `next_review_at: 2026-11-17T22:30:00Z`. Reviewer run `35ea4b72d5d749ce8831417bf672d3a9`.

Bot code, manifest and named Solidity executor source are byte-identical to the hashes in the prior technical approval. `manifest-check.py --all` passes. Only paper state changed since the previous review. `gate status` at 20:22 UTC shows ten live `trial-*` directories and no freeze. This includes `trial-aave-optimism`, whose promotion funded a $15.02 wallet but failed to deploy its executor; it is inactive, still counts toward X and the live trial cap, and was reported to the human. Recheck capacity after operator recovery. No new fork reproduction is needed for unchanged approved source.

# Review 2026-11-17 17:10 UTC — wait (cheap-chain trial capacity)

Decision: **wait — prior cheap-chain trial technical approval stands; ten trial bots remain live**. `next_review_at: 2026-11-17T19:00:00Z`. Reviewer run `4f7118b6333f4ef9999b9ea8aeca8f55`.

Bot code, manifest and named executor source remain byte-identical to the SHA-256 hashes in the previous technical review. Only paper state changed. `gate status` at 17:07 UTC showed ten live `trial-*` bots and no freeze; the human decision `2026-11-17-cheap-chain-trials.md` limits simultaneous live trials to ten. Recheck when a slot opens.

# Review 2026-11-17 14:02 UTC — wait (cheap-chain trial capacity)

Decision: **wait — cheap-chain trial passes technical review; ten trial bots occupy the live cap**. `next_review_at: 2026-11-17T16:00:00Z`. Reviewer run `81b91c467a524277b92f6a7505dd8436`.

`manifest-check.py` and `forge build` PASS. Capital is $15, `max_loss_per_tx_usd` is $1, and there is no principal; the OP native wallet is under the $18 chain cap. The bot estimates gas, sets a signed fee cap plus $0.02 L1 allowance below $0.90 at its buffered ETH price, requires simulated USDC gross above that cap, and bids at most 50% of gross as priority fee. It watches confirmed Chainlink `AnswerUpdated` logs, scans on a timer, and rereads state on feed gaps and errors; there is no pending-transaction path. The live path takes `EXECUTOR_ADDR` and handles the signer address dict; paper mode only simulates. The owner-only Solidity executor receives targets as call arguments, flash-borrows USDC, reverts without the specified USDC gain, and transfers the gain to the bot wallet atomically. No setup transaction is needed.

I reran `scratch/trial-exactly-optimism/proof.py` on the Optimism fork from block 159512296 using the current artifact. The `NoProfit` guard `0x7f0f4f5e...8fc09027`, nonowner call, and healthy-account call reverted. Success `0xf8d6823f...0e7bde` used 1,018,339 gas and paid 22.020528 USDC to the owner. Executor USDC, WETH, native, and market/Morpho/router allowances were all zero afterward. `selftest.py` confirmed the bot calldata and its historical `best_take` result of 22.020528 USDC. Paper logs show lower-price feed rounds, scans, no live sends, and no current underwater account; natural capture is waived for trials.

Paid public entry within seven days: Exactly liquidation `0x058f8a4fd284eac508983529e00d15dbfce6b21d6eb2e717d385ca26b7c3653c`, block 159512297, with 434.373279 USDC repaid; the reproduced executor gain was $22.02, well above one send's gas. README census: 115 liquidations by six receiver contracts, 23 sampled takes of at least $5, four takeable at the parent block, with sampled priority fees from 944 wei to 20 gwei (median 0.0025 gwei). Projected relay plus feed use is 72,000 CU/day, about $0.038/day at $0.53 per million CU; code caps relay reads at 65,000 CU/day, and projected feed use is 24,000, below the 100,000-CU trial limit. Trial rules waive EV and capture-window classification. `gate status` shows ten live `trial-*` bots, so the policy cap prevents promotion now.

Source SHA-256: bot `e7e38c53661c7357537c13333d7646f298c032dff2874e562bb27c31691d0873`; manifest `bab377eead2737946737548f76d70d9610dcd33211fcf7325bad1d6f51056d8d`; executor source `611ef0927ecce503f3ca5bb0992eac3057090b912518943ff9672748be4f75c2`.
