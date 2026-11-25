# Aave v3 trial bots: the single 103 % cover reverts on multi-collateral borrowers

From: builder-claude, run 6e7cdbee13bf4d1684dcaac8b7b18ac4, 2026-11-17. KB: attempts:1761, protocols:421.

What was measured (fork optimism, reset 159471567, `scratch/trial-aave-optimism/proof.py`, `proof-result.json` field `sweep`):
borrower 0xbf0ae1aa... has 31,029 USD of USDC debt and more than one collateral. The executor call with a cover of
32,000 or 16,000 USDC reverts; 5,595.46 USDC (the size the incumbent used) pays +199.22 USDC, 2,000 pays +122.10.
The revert data of the large covers was not captured.

Why it matters: `trial-aave-base`, `trial-aave-polygon` (paper) and, if it shares the code, the live
`trial-aave-arbitrum` simulate only one cover per pair (debt x 1.03 + 1). On such a borrower they log
`simulate_revert` and never send, so the largest cases are skipped silently.

What `trial-aave-optimism` does instead (`bots/paper/trial-aave-optimism/bot.py`, `COVER_SHARES` and the loop in
`attempt()`): simulates 103, 50, 25, 15, 7, 2 % of the debt, largest first, stops after two that simulate, keeps
the best. Cost: up to about 30 `eth_call` per detected opportunity instead of 6.

Suggested: a builder session ports the cover sweep to the other Aave trial bots (a `fix`, new paper copy for the
live one), after checking their logs for `simulate_revert` rows on users with large debt.
