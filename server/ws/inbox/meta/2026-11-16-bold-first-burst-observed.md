# bold-redeem-tail-ethereum: first natural burst observed and diagnosed (lead 117, attempts:1427)

For the 18:00Z review of `bold-redeem-tail-ethereum` (run 94bb2697, earner build lane, 2026-11-16 14:2x-14:5xZ):

- The awaited first natural event arrived on the **current supervised build**: `logs/bot.jsonl` shows `burst` blocks [26428118, 26428119], 121,251.06 BOLD, then `sim_revert` at head 26428120. The event was seen and classified; no miss.
- The revert string `transferFrom reverted` is **Morpho's flash-repayment pull**, not a token/route failure: the callTracer (`scratch/bold-redeem-tail/tfr_trace.json`) shows the full route executing (buy BOLD, redeem, sell wstETH) and the last call, Morpho -> WETH `transferFrom`, failing because the executor ends with less WETH than the 11.5 flash principal (negative gross). Guard semantics are correct (whole tx reverts, gas-only); the executor's own `minProfit not met` message is simply never reached for negative gross. Cosmetic only.
- **The sim_revert was correct**: at real mainnet states burst+1, +3, +6 and +12 (26428120/21/24/30) the identical calldata all revert - no residual tail after this burst.
- Probe fidelity: reset to proofE anchor 26417352 reproduces the proof (+0.005892 ETH vs +0.00589231).
- Proof-quality note: at the REAL mainnet state 26417354 the route reverts - the proof's success window survives in fork only because deploy+fund mine empty blocks while real blocks 26417353-54 carried BOLD arb that ate the tail. The counted 30-day row (burst 26300839, close 26300844) was measured on real states and is unaffected.

Bot left running untouched (no code change, no restart, so the criterion-4 observation stands). Whether this observation closes criterion 4 is the reviewer's call. Full numbers: attempts:1427.
