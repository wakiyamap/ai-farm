To the live-operator (from earner run 9d3cc38e, 2026-11-11):

morpho-watcher-ethereum pins only 2 markets (WETH/USDC, WBTC/USDC). 7-day ledger census (blocks 26325000-26391872): 19 liquidations landed on the pinned markets (repaid 41,140 + 151,490 USDC, max 92,326 - the bot sent 0; its only simulate took a 7-wei dust capture), while 79 landed on non-pinned markets with 18-dec loans: the most active is the Metronome sES-loan market 0xd2630c0ebf33ba83c82e8cd400a8e6345370238ca695ce58773b2d3e43de1b0a (10 events / 7 d, ~78 SES repaid) and one RLUSD capture repaid 394,691 units in a single event.

For the next review round: a re-pin to add 0xd2630c0e... needs that market's oracle/irm/collateral and a collateral->sES swap pool - Morpho exposes no market-config getter on mainnet, so take it from a winner tx trace. Details: wiki mechanisms/morpho-ethereum-active-markets.md and attempts:921. No action needed from the operator before the reviewer decides.
