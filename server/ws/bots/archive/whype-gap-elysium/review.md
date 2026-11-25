# Review — 2026-11-15T12:05Z

Decision: **demote**
Run: `080cc76e65e94fc0883f59d5890902c3`
Next review: none (`next_review_at: null`); archive this closed route.

The bot's own payout route was closed after its last paper placement and after the preceding fix review. `attempts:1293` (`dead_end_recorded`, 10:57Z) recomputed the submitted 12 round trips as **-$5.86 per $100 over 26.5 h before gas**. The same-pool buy/exit loses to fees immediately (fork: 20 USDC buy, 19.9554 USDC exit), so its entry cannot satisfy the holding-frame cost-recovery guard. The measured alternative pool did not establish positive EV. Lead 184 is now `dead_end` and explicitly closes this bot's route. Under the closed-class review rule, further fix rounds and fork reproduction are unnecessary. `manifest-check.py` passes, but that does not reopen the payout route. The paper service is dead; no promotion attempted.

---

# Review — 2026-11-15T10:34Z

Decision: **fix**
Run: `466717176aed4cecbf57d227f37d36f9`
Next review: after the entry guard, live funding sequence, paper state and economics evidence change (`next_review_at: null`).

## Blocking findings

1. The holding-frame entry guard is below cost. `bot.py:255` sends `minExitUsdc = 0.995 * SIZE_USDC` (19.90 USDC for a 20 USDC buy), and `executor.sol:81-82` checks only `quoteExit >= minExitUsdc`. The holding-frame decision requires the acquired WHYPE to sell for **at least the full cost** at entry. `quoteExit` (`executor.sol:59-63`) is a spot/fee approximation and omits the sell's own price impact; it is not an executable full-size exit. The submitted fork path itself buys 20 USDC and sells back for 19.9554 USDC. A compliant entry guard must measure or conservatively bound the actual exit amount and reject a below-cost buy. If same-pool fees make this impossible, change the route rather than relax the guard.
2. The current paper service cannot test the changed code. It restarted at 10:08:09Z but loaded `state/state.json` with `holding: true`, `whype: 0`, `whype_est: 309824409318485345173504` (about 10^6 times the expected raw WHYPE amount), and no round trips. From restart through 10:31:59Z the log has 24 heartbeats and no new `sim_buy` or `sim_sell`. Clear the stale simulated position through the earner's paper workflow and show fresh executable buy and sell decisions. Also make a failed `executor_quote_exit` prevent `sim_buy`: `bot.py:233-242` still logs a buy when `q` is `None`.
3. Live funding is not sequenced. If the executor has under 20 USDC, `bot.py:244-257` broadcasts an ERC-20 transfer and immediately estimates/sends `buy` without checking the transfer receipt or success. The estimate can see `NO_USDC`, and a failed transfer does not stop the buy attempt. Wait for a confirmed transfer and re-read the executor balance before estimating or sending the buy.
4. The revised README's 12-row historical table sums to **-$5.87 per $100** from its rounded rows (-$5.86 using its unrounded claim), or about **-$1.17 per $20 position over 26.5 h**, approximately **-$1.06/day before gas**. The earlier +$12.79 per $100 claim (attempt 1276) is contradicted by the later recomputation (attempt 1288). The table has no gas for either leg. A new per-round-trip table with actual buy cost, sell proceeds, both gas charges, negative outcomes, and entry/exit eligibility times is needed; at present recomputed EV is below the read cost, so promotion is unavailable.

## Checks

- `manifest-check.py`: PASS. `allowed_contracts: []`, `holding_usd: 20`, `principal_usdc: 20`, `holding_max_hours: 24`, and a Solidity executor with no constructor target are present. The named lead 184 is `measured`, with no later dead-end attempt. No human decision from 11-13 through 11-15 excludes this route.
- Read cost: 10-second slot0 polling = 8,640 `eth_call`/day at 3 CU = **25,920 CU/day**, about **$0.0137/day** at $0.53 per million CU, before opportunity quotes and transaction checks. The latest measurable EV is negative before gas.
- `sell` leaves USDC in the executor (`executor.sol:87-100`). This can be working capital for another entry, but the bot needs a documented path to return proceeds to the wallet at its stop/timeout and before live-loss accounting; `exitAll` is the only current payout path and is never called by `bot.py`.
- Fork success and guard revert were **not independently reproduced in this review** because the entry guard fails the holding-frame rule and the current paper run cannot establish detection or EV. The previous review's fork objection about direct swaps was corrected by attempt 1288's sentinel finding, but that proof is not promotion evidence until independently reproduced, including the delayed `exitAll` case.
- Gate status: intermediate Elysium balances are 0 HYPE and 0 USDC. No promotion attempted; this is not the deciding blocker.

---

# Review — 2026-11-15T09:01Z

Decision: **fix**
Run: `b0af3569bbb24303a43a878520b519ad`
Next review: after code, artifact, manifest, and paper evidence change (`next_review_at: null`).

## Blocking findings

1. The named executor cannot buy or sell through pool A. Its `buy`, `sell`, and `exitAll` call `pool.swap` directly. The manifest itself says the pool's hook rejects a fresh contract and that router integration remains open. `scratch/whype-gap-elysium/proof.out` has `NO_REVERT_BUG` for the intended guard test and shows 0 WHYPE, unchanged 20,000,000 USDC, and `exitPool=0` after the attempted buy. Its successful `exitAll` only moved idle USDC. There is no successful held-position exit, timed exit, or profitable fork round trip to reproduce. Replace the swap path and supply a fork proof of a successful buy, price guard revert, immediate and post-24-hour `exitAll`, stranger revert, and zero residual balances and approvals.
2. Paper execution does not model a real fill. At 08:37:53Z `quote_error` reports arithmetic overflow, immediately followed by `sim_buy`. The `whype_est` expression in `bot.py:223` multiplies raw 6-decimal USDC by `10**18` instead of converting to 18-decimal WHYPE, overstating the held amount by 10^6 (`~3.08e23` raw versus `~3.08e17` raw). The paper log has no completed round trip and no simulated transaction. Make paper decisions depend on an executable quote and valid simulated fill; rerun long enough to capture exits.
3. The live gas estimate uses `from: EXECUTOR` for an owner-only entry (`bot.py:146`); `onlyBot` will reject that sender. The USDC transfer uses a fixed 200,000 gas limit (`bot.py:231`), contrary to the Elysium Nitro estimate requirement. Estimate each wallet transaction with the bot wallet as sender and the right target and state.
4. The buy guard accepts `minExitUsdc = 99.5%` of the 20 USDC cost (`bot.py:237`), while the holding-frame rule requires the received asset to be sellable for at least its cost at entry. `quoteExit` is a spot calculation, not a full-size executable exit quote. Enforce the required cost floor using the actual exit path and demonstrate a price-based guard revert on the fork.
5. README gives aggregate 12-round-trip backtest figures but no per-round-trip table of cost, proceeds, both gas charges, and negative outcomes, nor measured entry/exit windows for this submission. Recomputed eligible EV is therefore **unavailable**, so the stated ~$2.3/day cannot support promotion. The paper observation is only about 23 minutes old. Provide the table and a second observation window before resubmission.

## Checks and economics

- Manifest static check: PASS. `allowed_contracts: []`, `holding_usd: 20`, `principal_usdc: 20`, and `holding_max_hours: 24` have the required shape. Solidity source matches the named artifact's source; current hashes: manifest `08d04ea7`, bot `87ce7596`, executor `f8809ed0` (SHA-256 prefixes).
- Read cost: 10-second `slot0` polling = 8,640 `eth_call`/day × 3 CU = **25,920 CU/day**, about **$0.0137/day** at $0.53 per 1M CU, plus event-driven quote calls. EV cannot be compared credibly until the round-trip table and executable path exist.
- Claimed pool USDC balance is ~$59,625, about 2,981× the $20 holding cap; this is carried from the README, not independently verified for promotion. The asset is a same-chain swap asset with no stated lock or redemption wait, so this is a fixable implementation case rather than an out-of-frame demotion.
- Gate status at review: 0 Elysium native and 0 Elysium USDC in the intermediate wallet. No promotion was attempted because the bot fails the mechanism and evidence criteria.
