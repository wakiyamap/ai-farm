**Decision: promote** (cheap-chain trial) — 2026-11-20T19:30Z, run `f525d62e330540b2987463e7aceb3436`.

`next_review_at: null`. The non-liquidation ICHI vault price arbitrage is expressly allowed by `decisions/human/2026-11-21-ichi-yes-peapods-fee-no.md` (saved 2026-11-20 18:13Z). `manifest-check.py` PASS; HyperEVM, `capital_usd: 20`, per-send cap 0.95 USD below the trial's 1 USD bound, executor-only wallet sends (`allowed_contracts: []`). The current human trial cap is 60 (`decisions/human/2026-11-21-trial-slots-60.md`, saved 2026-11-20 18:20Z); after three older parked promotions, 58/60 live trial slots are occupied.

## Independent fork reproduction

I reran the artifact proof at parent block 51,781,938, then ran `scratch/trial-ichi-vault-hyperevm/reviewer-proof-f525d62e.py` with the bot's exact 500,000 USDC flash size. Results: deploy 1,188,466 gas (<2,000,000); owner USDC +8.182419 after success tx `0x3538a40d916dd92fb68b57c90527324b4f9860db9d7ea020b728a352c04ed117`, gas 734,408; high-minimum guard tx `0x7ecef02b31bf87c90aab9178b97dbc6e397be7026794c5c9298c901607bc873d` and post-capture repeat `0xf73f0aa193c9bf900999b4ec68b6ab822738b63a1c19e031130465dfa5b9946d` reverted. Non-owner call reverted. Executor USDC, WHYPE, vault shares and both checked allowances were 0 after success. The fork uses replayed outputs for the two HyperCore read precompiles, taken from the named real incumbent trace; vault, sell pool, Morpho and token code/state are unmodified. This is a historical-state proof; live sends still require a fresh profitable scan and exact-call simulation.

## Trial criteria

The executor's `run` is owner-only, single transaction, deadline-bound and requires positive USDC profit at least `minProfit`; it transfers the full USDC balance to the bot wallet. The bot estimates gas before every live send, limits to 1.9M gas, caps `gasLimit × maxFeePerGas` at 0.95 USD using a 15% HYPE price margin, requires simulated gross >= 1.2× gas cap, sets `minProfit` above the gas cap, and caps priority bid to 35% of gross. The signer applies its own price and L check. No startup RPC bypasses its 98,000 CU/day handler. One `scan()` every 27 s is 3,200 × 26 = 83,200 CU/day; the hard cap is 98,000 CU/day = $0.052/day at $0.53/1M CU. No feed or mempool watch. Every live send logs result, gas and winner block gap. The README names 248 paid same-transaction vault round trips in the last 7 days; tx `0xcd7b75eb3282676f5fdc0da9c57c6e8e1ab7d9f6b5f3b8465565748c106dad61` paid 8.172130 USDC gross, above one send's capped gas. Public vault deposit/withdraw and Morpho flashLoan are callable by a fresh address. Paper logs show normal scans with zero available gain; natural capture is waived for cheap-chain trials.

---

