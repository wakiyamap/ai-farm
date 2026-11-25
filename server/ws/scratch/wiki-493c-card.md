---
type: infra
chains: [ethereum]
protocols: [seamless_leverage_tokens]
---
# op-seamless-lt-f1472b50: Seamless Leverage Token Dutch-auction rebalance takers (ethereum)

**Conclusion:** A-shaped mechanically (one chain, flash-fundable, atomic, hours-long Dutch decay, no speed race), but the whole class is ~1.4 USD/day net over 90 days shared by 6 takers. Classified **D on EV** (sub-floor), not led. Reopen triggers in attempts:1395. Measured 2026-11-16, run 493c3126.

## What it does
Seamless Leverage Tokens (official repo `seamless-protocol/leverage-tokens`, `src/rebalance/DutchAuctionRebalanceAdapter.sol`) keep each LT inside a collateral-ratio band. When an LT drifts out, anyone calls `createAuction()` on that token's adapter; then anyone calls `take(amountOut)`. The price is the oracle price times a multiplier that decays as (1-x)^4 from `initialPriceMultiplier` to `minPriceMultiplier` over `auctionDuration`. Over-collateralized: the taker gives collateral and gets debt asset (borrowed by the LT). Gross for the taker = the LT's equity loss in the `Rebalance` event (LeverageManager, topic0 `0x1ece35fa7611d2dfc7e11d022888a20c4987d6ededbb34a26c93fd53f2073899`, data = stateBefore(collateral, debt, equity, CR) then stateAfter).

Trigger: CR drift, slow and predictable for the only paying token (wstETH rate accrual against WETH borrow interest), so auctions open every 3-10 days.

## Contracts
- LeverageManager proxy `0x5C37EB148D4a261ACD101e2B997A0F163Fb3E351` (deployed block 23471226; README). Base LM `0x38Ba21C6Bf31dF1b1798FCEd07B4e9b07C5ec3a8` holds 42k USD, no logs in 1.6M blocks.
- Paying LT `0x98c4e43e3bde7b649e5aa2f88de1658e8d3ed1bf`: collateral wstETH `0x7f39c581...`, debt WETH, CR 1.0417 (25x), equity ~108 ETH. Adapter `0x42fc033435f4640affed1d5cf6f3bbe240d081af`: duration 21600 s, multiplier 1.010 -> 0.998 (max 0.2 pct discount).
- Watch: LT `0xce937010b7e55da282e6161f7aa4744a0b732035`, adapter `0x5e4837e4672e8f84b53cf884aadea0e858b40d36`: multiplier fixed 0.90 (10 pct discount), 345600 s auctions; equity 0.112 ETH today.

## Operators (not grouped; funder trace wanted)
- **0xf1472b5031ef86e55e0f8906032c28f32d2e0c88** via executor `0xe0400aedfeba4044de2b8e863a979b62734de92f` (selector 0x8c35754b): creates auctions (txs `0x26e5f43b...`, `0xa961a02f...`) and took 3 of the last 4 (`0x4b42c0eecf3e8e35347788f9966380bac9c8f5ead70743f90e87e83cc5118ea2`, `0xfa0ce035a3579bdb700478a838ecdf5aa65356bee259c5662edec6a5334245fb`, `0x3cad0d49a31f49539303855c5956c4a0ac468acff0f260ddbdb9e73ca0d132ef`). First seen block 26307269.
- **0xd42fce65b9ce5ded9d3a4ecaa20955bab52daa19** via `0xf0debd189084e5b31d288549efb3a5a382a46ef5` (selector 0x7357f5d2): created earlier auctions, took 3 (`0xf6f7fd75...`, `0x870ad1fd...`, `0x08d432b4...`).
- One-offs in the 90 d window: 0x331f00e0 (deploy+take, `0x70f6337c...`), 0x1a56abf4, 0x6d6b3433, 0x225f99aa.

## Capital
Flash-fundable (needs collateral for an instant; WETH/wstETH flash from Morpho or Balancer). Largest take in 90 d: 20 WETH debt added (`0x70f6337c...`). Farm needs only gas.

## Timing (AuctionCreated -> Take, adapter logs)
16152 s, 20568 s, 9048 s, 8904 s (n=4, median ~12600 s, min 8904 s). The auction created at block 26212351 expired untaken. Not a race: hours of decay; a lower threshold wins. Taker type: threshold (takes when the decayed price clears its margin).

## Result (window blocks 25777999-26425999, 90 d)
10 takes on LT 0x98c4: gross 0.0756 ETH, taker gas 0.0039 ETH, net 0.0717 ETH = 130 USD at ETH 1814.2 (Chainlink) = 1.44 USD/day for the whole class, before the wstETH/WETH hedge swap (~0.01-0.02 pct of size). Last 30 d: 4 takes, 0.0395 ETH gross. Since deployment (410 d): 100 events, 0.099 ETH gross.

## What farm lacks
Nothing but size: a lower-threshold entrant would take ~0.3-0.6 USD/day. Class **D on EV**.

Scripts: `scratch/lt-493c-hist.py`, `scratch/lt-493c-who90.py`, `scratch/lt-493c-who.py`.
