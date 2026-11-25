# scout: every USD figure needs its token, decimals and price source (human, 2026-11-19)

## What happened

- scout attempts:2352 (lead 290, arbitrum gumball_protocol `GBT.treasurySkim()`) reported
  "$85.1 gross per call" from a pot of 48.0658 "WETH".
- builder-claude run f3e7c6e8 (03:55Z) checked before writing any contract: GBT22's `BASE_TOKEN()` is
  not WETH but 'GM' 0xfcd09dac09f64c6b94101c5d7d59a7a99b8846d5, which has no price. The reward was
  0.048 GM, cents at most. Lead 290 is dead_end. The builder's check worked; the scout's number was
  wrong by a unit, and it reached the brief and the human as an 85 USD opportunity.

## Asked of meta

Add a rule to scout.md (scout is at 39,460 bytes, the limit is 56,000), in your own words:

- Any USD figure in a KB row or session report names the token it was computed from: address (read
  on chain from the contract that holds or pays it, e.g. `BASE_TOKEN()`, `asset()`, `token0()`, not
  assumed from the pool's name or a protocol's docs), its `decimals()` read on chain, and the price
  source with its time (e.g. coins.llama.fi, timestamp).
- No price for the token: write the amount in token units and `usd: unpriced`. Do not substitute
  the price of WETH or any other token.
- A gross above 10 USD per call on a dormant protocol (no calls of that function in 7 days): say in
  the row that it is unverified and why nobody has taken it, if known.

Also consider whether builder.md and paper-reviewer.md need the same line; the builder already
caught this case, so it may be enough to keep its check as is.

Report the change (file, bytes after) in your next run.
