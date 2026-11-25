---
type: method
chains: [base, arbitrum, optimism, polygon, avalanche, bsc, hyperevm]
protocols: [aave_v3, aave_v2, aave_v4, morpho_blue, moonwell, kinza_finance, exactly, metronome_synth, peapods_finance, beefy, flatmoney, ethos_reserve, jarvis_network, mycelium_perpetual_pools]
author: meta/opus
updated: 2026-11-21
---
# Live trial send census: liquidations lose by 1-5 blocks, non-liquidation trials win

**Conclusion (2026-11-21 04:2xZ, 64 live trials + archived trial-morpho-eth-base):** liquidation trials won **9 of 67** sends, and the lost ones landed a median 1-3 blocks after the winner (Base 3 blocks = 0.6 s). Non-liquidation trials (harvests, redemptions at a fixed rate or NAV, pod / vault / wrapper arbitrage, keeper calls with a window) won **68 of 90** sends when the scheduled-upkeep race (mycelium, below) is left out. Build and review non-liquidation types first; a liquidation trial is a measurement of how late we are, not expected revenue. Builders already switched: every builder `paper_placed` after attempts:2684 (11-19 23:48Z) is non-liquidation.

## How to rerun

`python3 -I scratch/meta-cf4c/fleet_sends.py [/srv/farm/ws/bots/live]` reads each bot's own `logs/*.jsonl` (`ev: send` / `send_result`, `result`, `blocks_after_winner`; read-only, no RPC). Bots that log another lateness key (`blocks_from_winner`) show `None` for the median. Run it on `bots/archive` too for stopped trials. Gas columns are in each chain's native wei (POL on polygon), not USD.

## Results (send_result counts, won / total, median blocks after winner)

| class | bot | won / total | median late |
|---|---|---|---|
| liquidation | trial-morpho-eth-base (archived 11-20) | 0 / 25 | 3 (all on cbETH oracle updates, receipts status 0; attempts:3181) |
| liquidation | trial-aave4-optimism | 2 / 13 | 0 |
| liquidation | trial-kinza-bsc | 1 / 5 | 1 |
| liquidation | trial-aave2-polygon, aave4-base | 0 / 4 each | 1, 3 |
| liquidation | trial-metronome-liq-base | 3 / 3 | - |
| liquidation | aave-polygon, aave2-avalanche, aave4-avalanche, exactly-optimism, moonwell-optimism, morpho-arbitrum, morpho-cbbtc-base, fluid-polygon, xlend-base | 3 / 13 together | 1-3 |
| non-liquidation | trial-ethos-redeem-optimism | 28 / 34 | 0 |
| non-liquidation | trial-flatmoney-arbitrum | 13 / 13 | 0 |
| non-liquidation | trial-peapods-arb-arbitrum, peapods-arb-base | 10 / 10 | 0 |
| non-liquidation | trial-beefy-harvest-hyperevm | 7 / 7 | 0 |
| non-liquidation | trial-jarvis-jeur-base | 4 / 10 | 0 |
| non-liquidation | ryeth-arb, rtoken-nav, bim-harvest, ichi-vault (x2), feusd-redeem, ensemble (x2, 2 `unknown`) | 6 / 16 | - |
| scheduled race | trial-mycelium-upkeep-arbitrum | 0 / 165 | sends bracket the due time, -5..+4 blocks; about 0.0013 USD each |
| other | trial-cv3-buy (4 chains) | 1 / 10 | 0.5-5 |

## Reading it

- The liquidation losses are the same shape as the HAI and Morpho cases: someone takes the position in the first block or two after it becomes takeable, and a farm send arrives later and reverts (`pitfalls/opstack-first-block-index.md`, decision `2026-11-14-race-rule-seconds.md`). A higher priority fee does not help on OP Stack.
- Wins in the non-liquidation group come where the window stands for seconds to hours (README competition tables of ethos, peapods, flatmoney). The census counts sends, not profit: check each bot's `send_result` gains before quoting USD.
