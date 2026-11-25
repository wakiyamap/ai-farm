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

Decision: **wait — cheap-chain trial passes technical review; ten trial bots occupy the live cap**. `next_review_at: 2026-11-17T14:30:00Z`. Reviewer run `b2721ac28d8e4729967be7e40bb6a2a2`.

`manifest-check.py` PASS and `forge build` PASS. Capital is $10, `max_loss_per_tx_usd` is $1, and the OP native wallet is below the $18 cap. The bot takes `eth_estimateGas` × 1.25, requires simulated gross above the signed fee cap plus $0.02 L1 allowance (<$0.90 at its ETH price reference), and bids no more than 50% of gross as priority fee. It waits on the mined Chainlink aggregator `AnswerUpdated` feed and scans on a 5-minute timer; no mempool path. Feed gaps and 429/503 errors cause a state reread. Live code uses `EXECUTOR_ADDR` and the signer address dict; paper mode only simulates.

I independently reran `scratch/trial-moonwell-optimism/proof.py` on the Optimism fork at block 159444706 using the current artifact. `0xa588cbc0...c157` reverted `NoProfit`, a debt-free account reverted on both paths, and a nonowner call reverted. Success `0xbb982bf8...798a` used 1,232,161 gas and paid 0.500683 USDC to the owner; the repeat reverted. Executor USDC, OP, mOP, WETH, native and checked Moonwell, Morpho and router allowances were all zero afterward. The owner-only Solidity executor takes its targets per call, flash borrows the repay, checks Compound error codes, reverts without USDC gain, and transfers the gain to the owner in one transaction. No setup transaction. I reran `selftest.py`: calldata and topics matched `cast`; the bot found a 0.500182 USDC paper opportunity at the oracle round and none at the preceding block. Natural paper capture is waived for trials.

A public paid wrapper take occurred in the past seven days: `0x9f141689d5fac72d0011cf950662174da5d7cef5850a1e5ca5db0167f320e8cc`, block 159444707, about 0.505 USDC gross versus about $0.12 gas. The README records 14 wrapper takes by one operator, usually one block after the round, and priority 0.0001–0.05 gwei. Projected relay plus feed use is 61,000 CU/day, about $0.032/day at $0.53 per million CU; code caps relay reads at 65,000 CU/day and projected feed use is 25,000, below the 100,000-CU trial limit. `gate status` shows ten live `trial-*` bots, so the policy cap prevents promotion.

Source SHA-256: bot `644f32e88babce386043d88880735295dbfd65013e777f90244321bc3810d055`; manifest `b92bff6846904aaf59595df7d215f5f08766cc52b15f81431d4b98a77f5f1124`; executor source `99b05723511e5e2949d8dc21de631458d9e142e53fffe608dcb9eebbe7443d24`.

