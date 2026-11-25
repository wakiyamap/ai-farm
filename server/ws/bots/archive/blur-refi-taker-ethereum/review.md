# Decision: demote

Run: 470dcb37be934b2abc3d6a1085a2acd3 (2026-11-12 UTC)
Next review at: none; archive.

Attempt 969 (`dead_end_recorded`, 2026-11-12T02:56:50Z) postdates the last `paper_placed` attempt 967 and closes this bot's own Blur Blend refinance payout route. Lead 148 is `dead_end`. The 30-day census (blocks 26308223–26394623) found only one fill within the 50 USD per-transaction loss cap, with approximately zero interest. The route also holds principal in executor Pool units until a later repayment, outside the atomic loss guard and the watchdog's native/USDC wallet accounting. The previous `fix` findings stand, but another fix round cannot make this route pay at farm scale. Archive under the closed-class rule; no fork reproduction is needed.

---

# Decision: fix

Run: fca7ca293a0f457bac8a02bcc07350a6 (2026-11-12 UTC)
Next review at: after an atomic route and an executable detector/sender are placed.

`manifest-check.py` now passes, and the paper service is running. Promotion still fails three independent requirements:

1. **L is not enforced.** `receive()` moves a proposed 0.19 ETH float from the bot wallet into Pool units held by the executor. `take()` then spends up to that float to acquire a lien, leaving principal exposed until a later borrower repayment. Only a subsequent `sweep()` can return value to the wallet. `TakeTooHighDebt` caps the *amount invested*; it does not make the bot wallet whole in the same transaction. `SweepUnderwater` and `SweepNoProfit` protect only the later sweep. The manifest's $5 gas-only worst-case claim is false for the take route. The fork proof deliberately mints a simulated repayment before sweeping, so its positive final delta cannot establish the required atomic profit guard. This is the same substantive blocker as the two prior reviews.
2. **The paper detector cannot see the intended events.** `blur_refi_taker.py:19-26` builds topics with Python `hashlib.sha3_256`, which differs from Ethereum Keccak-256. For `StartAuction(uint256,address)`, it computes `0x3b8c90a5...` while `cast keccak` returns `0xe5095dc3...`; `Refinance` similarly computes `0x2ddc0f70...` instead of `0x558a9295...`. `eth_getLogs` will return no matching events. The paper log has only a start and poll at 02:45Z; it has no event detection or simulated send.
3. **No execution path exists.** The runner only logs `take_bid`. It never reconstructs the nine-field lien tuple, calls `take_calldata`, invokes `eth_call`, funds the executor, calls the signer, or calls `sweep`. The comment promises a later trace lookup but has no implementation. Thus the current bot cannot take an auction in paper or live mode, even after fixing topics.

The README also gives only aggregate window statistics, not the per-occurrence blocks and seconds required by `decisions/human/2026-11-12-morpho-stop-researcher-runs.md`. Its economics are internally inconsistent: 23 fills/day × $0.14 gas/fill = $3.22/day gas versus $1.13/day stated gross, before reads. The census says 220 fills/30 days (~7.3/day), not 23/day. Its 0.15M CU/day estimate assumes ~10 CU per log read, while the existing Reserve review uses ~200 CU for `eth_getLogs`; at a 15 s poll and roughly 12 s Ethereum blocks, that method alone could cost about 1.15M CU/day (~$0.61/day). Reconcile event counts and measure the actual live read plan before another promotion review.

No fork replay was run: the source and runner fail mandatory L and execution criteria independently of the fork's outcome. Source, manifest, and runner were read; `manifest-check.py` passed; paper status was active. 

---

# Previous review: fix

Run: 46c482af3aa44d0085e4a6e84fbe3798 (2026-11-12 UTC)
Next review at: after a complete manifest and runnable bot are placed.

`manifest-check.py` still FAILS: `manifest.yaml` does not exist. The service is inactive/dead and the directory has no bot code or paper logs. The changed `BlurRefiTaker.sol` now deposits received native into Blur Pool units, resolving the prior missing-deposit issue, but `take()` still spends those Pool units to acquire a lien repaid only at a later event. The bot wallet loses principal in the first transaction, and `take()` has no same-transaction wallet-balance profit guard. `sweep()` can only pay later; it cannot repair L for `take()`. The new source SHA-256 is `7fa45b75c89c54adc8a7bdc15f8ca835e10bb42e165f6bea0444ea656758fe47`. Provide an atomic, profitable route that returns principal and profit to the wallet in one transaction, plus the missing manifest and runnable bot. No fork reproduction was warranted after the mandatory manifest failure.

---

# Previous review

Run: 1e299b54c0a14bf0bdcc96d054901666 (2026-11-11 UTC)
Next review at: 2026-11-12T00:15:00Z, or sooner after a complete bot is placed.

`tools/manifest-check.py bots/paper/blur-refi-taker-ethereum/manifest.yaml` fails because the manifest does not exist. The directory contains only a Solidity source and build artifacts; there is no bot code, run script, README, paper log, or deployment declaration to review. The service is inactive/dead. Add the complete manifest and runnable paper bot, then pass the manifest check before review.

The present contract also cannot meet L as written: `receive()` moves funded native into WETH, while `take()` spends Pool tokens to acquire a lien claim and `sweep()` pays interest in a later transaction. The bot wallet loses its principal before the later liquidity event, and the principal remains outside the bot wallet where the watchdog and sweep do not count it. `take()` has no same-transaction bot-wallet end-balance guard. An atomic profitable route with principal returned in the bot wallet is required before promotion; a two-transaction loan/investment position is outside this system's L rule. The source also shows no Pool deposit after wrapping native to WETH, so the funded float does not become the Pool tokens that `take()` needs.

No fork work was run because the manifest check is a mandatory fail. Current source SHA-256: `2ab17252c381f383a3f08a02f43f71ce8892ec5a6c25e6a4468f31e36482b544`.
