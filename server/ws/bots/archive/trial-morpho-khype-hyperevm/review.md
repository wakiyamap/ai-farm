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

Source SHA-256: bot `e4689b2b4309438d07e556b00fc2d54c137fc48ab39a45d00dd75b01e1263b59`; manifest `889331d812718c1bed3b34abc5052c887fa40670bd69df4fa1d2c3afac72829b`; executor source `3906bd1cfb17f0c060349765aa714fd45f5434605573a6c668e38f61ebcf00ce`.

# Review 2026-11-17 09:19 UTC — wait (cheap-chain trial capacity)

Decision: **wait — prior cheap-chain trial technical approval stands; ten trial bots remain live**. `next_review_at: 2026-11-17T11:30:00Z`. Reviewer run `99cd382d51904b98816c9497e673b64f`.

Only paper state files changed since the 06:07 review; bot, manifest and executor source are unchanged. `manifest-check.py` still passes. The previous review independently reproduced profitable wallet payout, `NoProfit` guard revert, empty executor and the bot's send path, with a sub-$1 fee cap and about 51,000 CU/day ($0.027/day). HyperEVM intermediate native is now about $68, enough for $20 bot funding plus deploy gas, so the earlier funding shortfall has cleared. `gate status` still shows ten live `trial-*` bots. Recheck capacity at the next review; no fork rerun is warranted for unchanged code.

# Review 2026-11-17 06:07 UTC — wait (cheap-chain trial capacity and gas funding)

Decision: **wait — cheap-chain trial passes technical review; ten trial bots are live and HyperEVM gas funding is short**. `next_review_at: 2026-11-17T08:15:00Z`. Reviewer run `ede2e9362aad4dd5951d1c6f67165c34`.

`manifest-check.py` PASS. `forge build` PASS. Current Solidity executor has only owner in its constructor; market, borrower, size and both sale pools are per-call arguments. Its owner-only entry liquidates through public Morpho, sells kHYPE to USDC inside the callback, approves exactly the repayment and resets approval to zero, reverts NoProfit unless USDC grew, and sends USDC to the bot wallet. No setup call or baked target. The bot uses the signer dict and live `EXECUTOR_ADDR`, never the fork address in live. It reads mined state only and sends when gross exceeds that send's gas cap. Its 700,000 and 1,900,000 gas limits are below HyperEVM's 2,000,000 limit; priority is <=40% gross, fee cap sized to < $0.95 at its oracle reference. It logs each send's result, gas and winner block. Capital $20 and loss/tx <$1.

I independently reran `scratch/trial-morpho-khype-hyperevm/proof.py` on the HyperEVM fork at block 51482424. Deployment used 1,025,463 gas. A fork-created borrower became liquidatable after interest accrual. High-minimum tx `0x5715ba3e...d460d67a` reverted NoProfit, and a healthy borrower and nonowner reverted. Success tx `0xa363bb3f...a4b16246` used 430,424 gas and raised the owner's USDC by 198.487910; borrower debt shares fell to zero. Executor USDC, WHYPE, kHYPE and Morpho allowance were all zero. I reran `selftest.py`: historical pre-winner block 51257132 simulated +149.180011 USDC; the same borrower was healthy one and two blocks earlier. Its full head scan found one dust candidate and correctly skipped it because $0.003428 gross was below $0.013142 gas cap. One first selftest `discover()` call failed because `eth_getLogs` saw a provider head behind `eth_blockNumber`; retry passed and normal paper scans continue. This is a transient discovery read, not a payout or loss-guard failure.

Paid-entry evidence is the direct-route tx `0x4da0c91c...a44f2fb` in the past 7 days: the same public `liquidate` entry had a simulated $149.18 gain one block before its capture. The README lists 18 >=$1 liquidations on the two markets by 8 EOAs and 11 callers; direct-route winners paid 278-3,393 gwei priority and usually took in 1-2 blocks. Trial rules waive the speed class and natural paper capture. Timer reads are about 51,000 CU/day = $0.027/day at $0.53/M CU; code hard cap 90,000 CU/day = $0.048/day. Fast timer is 2 s only when a >=$200 debt is within 0.7% of liquidation and the budget permits.

`gate status` at review showed ten live `trial-*` bots. HyperEVM intermediate native value was $19.83, below this bot's $20 funding plus deployment gas; promotion cannot be attempted until funded. Recheck capacity and funding at `next_review_at`.
