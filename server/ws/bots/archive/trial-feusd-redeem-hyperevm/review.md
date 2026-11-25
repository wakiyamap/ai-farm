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

Source SHA-256: bot `225e732cdb3a605601242e2b22b54d6a829d806fee28c0a42e009e07471aff8a`; manifest `419d468c1da1ead58ca51887121c2eef78e57cc36c73f83c5700cf2dbca6bb38`; executor source `9379968f8c9e720e7811d2a75fbf50d7393f359e8d32719a819cba52441fc8c8`.

# Review 2026-11-17 09:19 UTC — wait (cheap-chain trial capacity)

Decision: **wait — the feUSD dust fix passes the cheap-chain trial review; ten trial bots occupy the live cap**. `next_review_at: 2026-11-17T11:30:00Z`. Reviewer run `99cd382d51904b98816c9497e673b64f`.

`manifest-check.py` PASS and `forge build` PASS. The revised owner-only `FeusdRedeemTake.take()` returns Felix's 1-wei feUSD rounding remainder to the owner before its native HYPE payout, then reverts unless the owner's native balance increased by at least `minProfitWei`. Morpho flash principal is repaid within that transaction. Route targets are call arguments, callback peers are active only during the call, approvals are exact and reset. The bot reads `EXECUTOR_ADDR`, obtains the signer address correctly, sends only in live mode, re-reads pool state on feed gaps and 429/503 errors, and records won/lost sends with gas and winner block. Capital $20, signed gas limit 1,950,000 below the HyperEVM 2,000,000 cap, `maxFeePerGas` at most 2 gwei and under a $0.95 gas cap at its HYPE price reference, priority bid at most 30% gross, and a send only when simulated native gain exceeds the signed fee cap.

I independently reran `scratch/trial-feusd-redeem-hyperevm/proof.py` at HyperEVM fork head 51494058. Deploy `0x0d5838a2...8d7616` used 1,160,496 gas. A stranger's public feUSD sale created a price window; success `0x57fd279e...79cf5` used 1,726,717 gas and increased the owner's native balance by 0.063908609485908561 HYPE after gas (gross 0.065682546076373513 HYPE). The no-window, nonowner and exhausted-window calls reverted. Executor USDT0, feUSD, WHYPE, kHYPE, native balance and four checked allowances were all zero after success. I reran the bot's historical `selftest.py`: calldata matched `cast`, and pre-incumbent blocks 51292212, 51359837 and 51431191 each produced a positive `paper_sim` whose gross exceeded its fee cap; head had no window. Paper logs show Swap and safety-poll rows without persistent errors. Natural capture is waived for this trial.

The current measured lead is 227; the older dead-end lead 149 was a different payout evaluation, superseded by the native-HYPE route. Paid-entry evidence is incumbent Felix redemption tx `0x30ba123ac9bbee2a970571688eb0805777455b5e23f528aec3241c91a8eb9613`; attempts:1591/1595/1605 count 83 paid of 96 calls over seven days, median gross $0.066 versus $0.018 gas per attempt. The README records two takers and their fee levels. Feed plus relay use is about 30,000–45,000 CU/day = $0.016–0.024/day at $0.53 per million CU, below the trial's 100,000-CU ceiling; relay reads are capped at 90,000 CU/day.

`gate status` shows ten live `trial-*` bots, so no promotion is allowed now. HyperEVM intermediate native balance is about $68, adequate for this $20 bot; the capacity cap is the sole present gate blocker. Recheck at the next review. Source hashes (SHA-256): bot `225e732cdb3a605601242e2b22b54d6a829d806fee28c0a42e009e07471aff8a`, manifest `419d468c1da1ead58ca51887121c2eef78e57cc36c73f83c5700cf2dbca6bb38`, executor source `9379968f8c9e720e7811d2a75fbf50d7393f359e8d32719a819cba52441fc8c8`.

# Review 2026-11-17 07:42 UTC — fix

Decision: **fix (cheap-chain trial)**. `next_review_at: null`. Reviewer run `8d82add30e4d46c38ebc9658577c7b80`.

The executor leaves 1 wei of feUSD after a successful take. My fork rerun at head block 51488305 shows success tx `0x3b45d3f191cfb9bee6f3742a11e2723d84c1f0bd3f813f838ca27ca6cef89a23`: owner gained 0.189895650282213337 HYPE after 1,744,687 gas, but `executor_left.feusd = 1` in `scratch/trial-feusd-redeem-hyperevm/proof-result.json`. The 2026-11-15 executor-shape decision requires zero token balances after the success tx. Return this rounding remainder to the owner or otherwise clear it inside the same transaction, then rerun the fork proof and check every token balance and approval. This is a shape fix, not evidence that the payout route is absent.

`manifest-check.py` passed. I read the Solidity and bot code: only the owner is a constructor argument, protocol targets are call arguments, the owner-only take uses a flash loan and reverts if the native payment to the owner is below `minProfitWei`; the bot sets that minimum to the signed gas cap. Its live branch takes `EXECUTOR_ADDR` and the signer address correctly, and paper sends nothing. The fork's no-window tx `0x7b62d021b0f95bb41311eef889bb24be2fa9dcf3aafe998884cee105b5f60aed` and nonowner tx `0x2c83b8d34ec5b3c1d6c8aee46141ce5f42c74007be5aa7f42d62a505e716349a` reverted. Deployment used 1,151,280 gas and the successful take used 1,744,687, both below HyperEVM's 2,000,000 gas cap. The bot caps the signed gas amount at 0.95 USD using the on-chain HYPE price and allows priority fees up to 30% of simulated gross; it sends only when simulated gross exceeds its gas cap. The code has a 90,000 relay CU/day hard cap plus a small Swap feed (estimated total 30,000–45,000 CU/day, 0.016–0.024 USD/day at 0.53 USD per million CU). Paper logs show safety polls and one Swap; natural capture is waived for this trial.

Past-seven-day paid-entry evidence is the public Felix redemption route of `0x0da1f154` through `0x1438e66b` (example tx `0x30ba123ac9bbee2a970571688eb0805777455b5e23f528aec3241c91a8eb9613`): 83 paid calls of 96, median gross 0.066 USD versus about 0.018 USD gas per attempt, as recorded in attempts:1591/1595/1605. The README identifies two competing taker addresses and their fee range. The current live count is ten `trial-*` bots, so the capacity cap also prevents promotion until a slot opens. The changed bot can be reviewed when its source and paper manifest are updated.
