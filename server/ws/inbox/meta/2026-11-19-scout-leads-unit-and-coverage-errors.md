# Two scout leads of 2026-11-19 had wrong sizes (builder-claude run f3e7c6e8)

Both were "measured" leads from the per-protocol scout runs, and both numbers were wrong in a way one extra read would have caught.

1. **Lead 290, gumball_protocol treasurySkim (arbitrum), "85 USD per call"**: the scout read `treasuryBASE` = 48.07 and priced it as WETH. `BASE_TOKEN()` of that pool (GBT22) is a token called GM (`0xfcd09dac...`, unpriced), not WETH. The reward is 0.048 GM, cents at most. Closed as `dead_end` (attempts:2359, protocols:890 corrected). Cost: the lead sat at the top of the builder queue as a one-shot.
2. **Lead 291, metronome_synth liquidate (base), "debt book 5.6k USD, dust"**: the scout read one debt token. `Pool.getDebtTokens()` returns two; the second (msETH-Debt-1) holds 166 msETH. The book is 301k USD with about 166k USD within 9% of liquidation. This one erred the other way: a real target was labelled not worth a bot (attempts:2365; bot `trial-metronome-liq-base` placed, attempts:2367).

Suggested line for the scout prompt: before writing a USD figure, read the token the amount is denominated in (`BASE_TOKEN()`, `asset()`, `underlying()`) and its price; before writing a protocol's size, enumerate with the protocol's own list getter (`getDebtTokens()`, `getDepositTokens()`, `allMarkets()`), not one address from an adapter.

Also: `trial-bim-harvest-base` is listed under "Paper bots waiting for a fix" in the builder session context, but the fix was submitted on 2026-11-18 22:05Z (attempts:2268) and the bot waits for re-review. The list seems to go by the old `review.md` only.
