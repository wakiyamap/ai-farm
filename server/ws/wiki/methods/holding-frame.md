---
type: method
chains: [any]
protocols: []
author: earner/qwen3.8-flash-next
updated: 2026-11-15
---
# Holding frame: buy with USDC, hold, sell back to USDC (up to 100 USD per bot, 200 total)

**Conclusion.** Since phase 12d (2026-11-15) a bot whose manifest sets `holding_usd` may buy another asset with USDC in one transaction and sell it back in a later one. It is the only exception to "the transaction reverts unless the balance ends higher". Use it for *buy at a discount, sell at market* (Dutch auctions, fee / revenue auctions), not for parking capital in yield (200 USD of yield is cents a day). Source: `decisions/human/2026-11-15-holding-frame.md` (Japanese, authoritative), common.md L, earner.md section 5, paper-reviewer.md "Holding frame".

## Limits (the gate refuses a promote before anything moves)

- `holding_usd` ≤ 100 per bot; ≤ 200 over all live bots (a bot half-stopped and still live counts). **First such bot: about 20** — the stop-and-sweep of a USDC-holding bot has not run with real funds yet.
- `principal_usdc` ≥ `holding_usd` (the buy is paid from the bot's own USDC).
- `holding_max_hours` present, 0 < h ≤ 168 (7 days). Past it, the bot sells by itself.
- `executor` artifact whose ABI has `exitAll()` with zero inputs.
- All three numbers are bare (`holding_usd: 20`, no inline comment): the gate parses the raw line with `float()`. `tools/manifest-check.py` checks all of the above.
- X, n, L unchanged: the buy transaction's gas is inside the 50 USD per-tx bound; 400 USD per bot.

## What is in and out

- **In**: an asset sellable to USDC **in one transaction at any time, on the same chain**.
- **Out** (record a lead with capital, holding time, worst loss and exit; stop): bridges, locks, redemption / withdrawal waits, queues, epoch boundaries — the exit can close for another reason while you wait. Cross-chain only if each chain has its own USDC and buys and sells inside that chain.
- Exit pool depth ≥ 10x the position; no asset whose price one small pool sets.

## Executor shape

- The bought asset stays **in the executor**, not the wallet. "Leave nothing in the executor" becomes "leave only the position"; still no left-over approvals, no baked targets (`pitfalls/executor-no-baked-targets.md`).
- **Buy entry**: arguments = max USDC to pay and minimum asset to receive; reverts unless what it received would sell for at least its cost in the exit pool right then.
- **Normal sell entry**: with a minimum-out argument. This is the bot's usual exit.
- **`exitAll()`**: no arguments, owner (bot wallet) only, sells everything, sends USDC to the bot wallet, returns without reverting when nothing is held, works in one tx at any time. It is the gate's door (`gate stop` calls it before the sweep) and the overdue exit; it goes to the public mempool with no minimum out, because the gate cannot compute one.
- The bot keeps its own stop price and sells at `holding_max_hours`.

## Pitfall: "sell for >= cost right then" kills a same-pool round trip (attempts:1293)

The buy guard (received asset must sell for at least its cost **in the exit pool right then**) can never pass when the entry venue and the exit venue are the **same pool** while the fee > 0: buying C and selling the receipt back immediately returns C x (1-f)^2 - the whype-gap-elysium fork proof numbers are exactly that (20 USDC buy -> 19.9554 USDC sell at fee 0.1152%/leg). A discount measured against an **external reference** (another chain's price, an NAV) is invisible to the on-chain quote, so a discount-capture holding-frame bot must either price the guard on a **different venue** (and measure that the venue really pays more at entry - Elysium pools A/B share the discount, so cross-pool quoting passed only 4.5% of entry samples at median -0.425%) or it does not satisfy the guard at all. Check who, on-chain, pays the reference at the moment of entry **before** building; whype-gap-elysium spent three sessions finding this out.

## Fork proof (reviewer reproduces it)

1. Buy succeeds; a buy at a bad price reverts.
2. `exitAll()` right after the buy, and again after `evm_increaseTime` past `holding_max_hours`: each time USDC is back in the bot wallet in one tx and the executor holds 0 asset and 0 USDC.
3. `exitAll()` from a non-owner reverts.
4. Exit pool depth measured, number in `review.md`. README states the worst loss (≤ `holding_usd`) and what has to happen for it.
5. EV per round trip = USDC back − USDC paid − gas of both transactions; losing round trips count negative.

## What nobody watches

- The **watchdog** stops such a bot at 30 + `holding_usd` USD loss since promotion (USDC moved into the asset is not counted as lost) and **does not see the asset's price**. If the bot does nothing, it can lose all of `holding_usd` before anything stops it. "The watchdog will stop it" is not a loss guard here.
- X does not count the position in the executor (looks up to 200 USD smaller).
- A profit left as the other asset is not swept; only native and USDC count.

## gate stop and exit code 3

`gate stop` calls `exitAll()` from the bot key, then sweeps. If `exitAll()` fails (reverts in estimate, not included, reverts on chain, USDC left in the executor), **nothing is swept, the bot stays live, exit code 3 "its holdings are NOT back"**. The human decides from there: the live-operator does not retry, it writes the `exit_failed` line to `inbox/human/`. After 3 failed transactions the gate sends no more. gate.log ops: `exit_sent`, `exit`, `exit_failed`, `exit_skipped`, `exit_gas_topup`.

## Daily spend

USDC the bot sends to the executor counts toward the day's `capital_usd`. A bot that makes several round trips a day either sizes `capital_usd` for that, or has the executor pull USDC via an approval of exactly the amount used inside the tx, reset to 0.
