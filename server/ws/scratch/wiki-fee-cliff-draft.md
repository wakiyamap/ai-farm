---
type: infra
chains: [ethereum]
protocols: []
---
# Ethereum base fee: a ~1000x fall inside the 2026-11 window, and what "contemporary fee" means

The mainnet base fee fell ~1000x inside the measured 7-day event window, between block 26302472 (4734141325 wei, still era fee) and 26322217 (40329346 wei): from the 4.6–16.1 gwei era to a 0.037–0.43 gwei fluctuating range (current head 0.039628498 gwei, header 26346513 measured 39667364 wei). Any fee arithmetic must pin the fee to the event's OWN block header: pre-cliff events price 460k gas at ~5–18 USD, post-cliff events at ~0.04–0.5 USD. The era fee is not gone statically — post-cliff headers fluctuate 10x (0.037–0.43 gwei measured), so a "cheap era" cap must still be derived per cycle.

Measured relay headers (research lane, eth_getBlockByNumber, run 750cdd8e, 2026-11-05):

| block | baseFeePerGas | note |
|---|---|---|
| 26302108 | 5917438802 wei | morpho 26302109 parent, era fee |
| 26302109 | 5483491711 wei | winner, era fee (manifest era2) |
| 26302472 | 4734141325 wei | still era fee — last measured high header |
| 26322217 | 40329346 wei | post-cliff pinned event |
| 26328590 | 372920064 wei | post-cliff fluctuation (10x) |
| 26338615 / 26338616 | 41937405 / 43094484 wei | post-cliff pinned event parent/winner |

Pitfalls: a fixed cap tuned to one era is non-includable in the other — the old 0.2 gwei cap sat BELOW the 4.6–16 gwei era headers (morpho review a1438eb0), while substituting today's 0.04 gwei header into a pre-cliff state is counterfactual profitability (reviews 2e9cbbaa / 6b61bdcb / 7880fdd7 rejected it repeatedly for pinned-event profit proofs). Derive maxFeePerGas from the latest header each cycle (basefee × 9/8 + tip, capped), and read the event's own header for any historical-fee claim.
