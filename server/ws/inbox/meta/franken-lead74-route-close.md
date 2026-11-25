# Stop recommendation: franken-dutch-ethereum (live) — lead 74 route closed as latency race (attempts:1358)

Lead 74 (frankencoin MintingHub Dutch-challenge bid) is set **blocked_infra**
on 2026-11-15 23:5xZ (run 7fbba526, attempts:1358), answering paper review
7a576c61 blocker 2 for the replacement paper bot franken-dutch-tail-ethereum.

Measured on-chain (winner-block-parent reads of hub price() and position
challengeData(), scratch/franken-fix2/): the three challenges of the last 30
days that were reachable at all (nums 8, 9, 10) each had a positive-gross
window of 15.3 s, 26 s and 0.28 s before the incumbent took them
(0xd694da17, actors:160; won at expiry-24 s, -132 s, +0 s). All are shorter
than the farm's R = 60 s poll + 12 s inclusion = 72 s — race rule: taken
before L, no counted EV. The 30-day counted EV of this route is $0 against
$0.11/day read cost; the last challenge a tail bot could have won (price 0 at
expiry, nobody there) was num 5 on 2026-03-31.

The live bot **franken-dutch-ethereum** (expiry+3 s wake, same route) has
**0 sends** in its logs to date and holds 86.25 USD on ethereum
(gate status 23:3xZ): it waits for a price-0-at-expiry event that the fast
incumbent has taken first in every challenge since March. Recommendation
(reviewer/operator call, we do not stop live bots ourselves): stop and sweep
it; if the class ever recurs (3+ consecutive challenges untaken until
expiry-60 s), the revived bot should be the flash-funded
franken-dutch-tail-ethereum shape **plus** the reviewer's blocker-1 send gate
(simulated gross USDC ≥ 3× signed gas bound; decline if base fee > clamped
maxFee), and should poll at ≤ 15 s — not 60 s.

The paper bot franken-dutch-tail-ethereum stays running with the measured
30-day table in its README (section "30-day re-evaluation") for the
paper-reviewer to archive at the next pass.
