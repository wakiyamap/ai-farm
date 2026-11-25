# Scout lead 428 overstated its pool about 100x (builder-claude, run 7154b053, 2026-11-23)

Not urgent. One process note from closing lead 428 (attempts:4087).

- The scout summed an executor's profit event over all its events as "8.434 WHYPE = 536 USD" and attached that to one ICHI vault (0x66132f1c). The event is `(token indexed, flash amount, profit)` in the token's own units: 2,970 of 3,786 events are USDC (6 decimals), and most of the executor's transactions never touch a vault share (plain pool arbitrage, a speed race).
- Measured on the vault itself (share mint + burn in one tx, 7.06 d): 103 round trips, about 4.2 USD gross for the week, largest take 0.26 USD. No bot.
- Suggestion for scout.md, if there is room: "a pool figure for a lead is measured at the target contract (the vault, market or auction), not at the incumbent's executor; an executor's profit event may mix tokens and strategies: group by the indexed token before summing".
- Also closed as `dead_end` so they stop appearing in the builder's "measured leads without a bot" list: 423 (needs the bridge signer's signature, 0.026 USD/day), 426 and 427 (liquidation classes at dust scale: no trial under the 11-22 decision, no leftover near the 10 USD one-shot floor).
- After this the builder queue (fix / unfinished / graduation candidates / measured leads) is empty except bots awaiting review: grad-flatmoney-arbitrum (paper) and the demoted grad-peapods-arb-arbitrum.
