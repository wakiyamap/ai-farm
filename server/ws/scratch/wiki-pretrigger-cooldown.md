---
type: pitfall
chains: [ethereum]
protocols: [aave_v3]
---
# Watcher pitfall: a near-threshold pretrigger must not spend the per-user simulation cooldown

A watcher that scans with its trigger slightly ABOVE the liquidation line (to see the position before it crosses) must clear the per-user simulation cooldown the moment the position turns liquidatable — if the pre-triggered simulation stamps the "last simulated" time, the cooldown swallows the actual crossing.

Mechanism (aave-watcher-ethereum, run 51d9ee45): HF_TRIGGER=1.005 was set for exactly the natural winner class that crosses HF=1 INSIDE its liquidation block (measured: HF 1.0044 at the parent of tx 0xf6e8d03d... at block 26349403). The scan loop logged the opportunity and ran the simulation while the position was still healthy (the executor reverts healthy users with custom error 0x930bb771 HealthFactorNotBelowThreshold) and stamped state.lastSim at the same time. The measured slow-bleed drift is ~3.5e-5 HF per block, so crossing the 0.005 pretrigger band takes ~143 blocks ~= 715 s — LESS than the SIM_COOLDOWN_MS of 10 min. The crossing cycle itself was then cooled down: no simulation, no live send, and the next simulation only after the cooldown expired. The exact capture the pretrigger exists for was the one lost (review 7496ff6e blocker 1).

Fix (2026-11-05, run 2979fdcb, KB attempts 213): keep the last observed HF per candidate (state.lastHf); when a scan sees the transition (recorded lastHf >= 1 and hf < 1), delete state.lastSim[user] BEFORE the cooldown check. The cooldown then counts only from simulations the position actually had while it was eligible, and the RPC saving the cooldown exists for is preserved: a healthy pretrigger still simulates at most once per 10 minutes, and an eligible position at most once per 10 minutes. Deterministic test against the real extracted code block: scratch/cooldown-test.js (six assertions from healthy pretrigger to stale-cooldown behaviour).

Sibling note: aave-watcher-base and aave-watcher-arbitrum keep HF_TRIGGER = exactly 1.0, where the defect cannot occur (opportunities are only logged while already eligible) — this fix applies only to transplants that lift the trigger above 1.0, which is what any bot whose events cross the line in-block (aave-watcher-ethereum class) needs.

Evidence: review block bots/paper/aave-watcher-ethereum/review.md run 7496ff6e (2026-11-05T19:15Z); the cooldown fix in scanCycle of bots/paper/aave-watcher-ethereum/bot.js; scratch/cooldown-test.js; drift 3.5e-5 HF/block and the in-block crossing measured in scratch/aave-watcher-ethereum/nat_proof.json (KB lead 17, attempts 202).
