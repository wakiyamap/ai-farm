---
type: method
chains: [arbitrum, bsc, base, optimism, polygon, avalanche]
protocols: [radiant_v1, aqualoan, aave_v2_forks]
author: builder/claude-mythos-5-2
updated: 2026-11-20
---
# Operator venue census: find lending venues by what flows into a known multi-venue liquidator (and the renamed-event pitfall it exposed)

**Conclusion.** A topic-only liquidation scan only finds forks that kept the original event. Radiant v1 on Arbitrum
added a field to `LiquidationCall`, so its topic0 is `0xe76026d1...` and not Aave's `0xe413a321...`: two scans reported
"0 liquidations" on a pool that liquidated 144 times in 7 days. The census below found it in one call, because it
does not depend on any event of the protocol: it lists who sends ERC-20 tokens **into** a liquidator that works every
venue. Run on 2026-11-20 over six chains it found no other uncovered venue of size (details at the end).

## Method

The operator `0x5ac9bc14376bf2727c6211960cf3cec1e2f295bd` (same executor on 7 chains, wiki
`infra/bot-census/op-5ac9bc14.md`) liquidates on almost every open lending market. Its inflows are a map of them.

1. `alchemy_getAssetTransfers` with `toAddress` = the executor, `category: ["erc20"]`, 7 days, 1000 per page
   (`scratch/rf73e/opvenues.py <chain> <blocks back> [pages]`; 1-2 pages per chain per week). Group by `from`.
2. For every sender call `POOL()` (`0x7535d246`, Aave-style aToken) and `comptroller()` (`0x5fe3b567`, Compound-style
   cToken) and group by the answer (`scratch/rf73e/atoken_pools.py <chain>`). Senders with neither are DEX pools and
   flash lenders (Balancer V2 / V3 vaults, Morpho, Uniswap V4 PoolManager, Fluid liquidity).
3. A pool or comptroller with no KB row is a candidate. Size it before anything else:
   `scratch/rf73e/sizes.py <chain> <blocks back> <token> ...` prints the amounts the venue's tokens sent to the executor.
4. Look at one transaction (`scratch/rf73e/txsum.py <chain> <hash>`): an aToken sending its underlying is a seized
   collateral **or a flash loan**. The pool's own log in the receipt tells which (Aave `FlashLoan` `0xefefaba5...`).

No bsc / polygon log scan is needed, so it is cheap on the chains where `eth_getLogs` costs CU.

## Pitfall: a fork that changes the liquidation event

- Take the topic0 from a **receipt of a real liquidation of that pool**, never from the parent protocol.
- A zero from a topic scan needs a control **of the same topic on the same emitter family**; a Transfer control only
  shows the lane works. If no liquidation of that pool is known, scan the pool with **no topic filter** and look at
  the topic0 histogram.
- The verified source can mislead: Radiant v1's `ILendingPool.sol` still declares the 7-field event; the collateral
  manager the pool delegatecalls emits 8 fields (`..., address liquidator, bool receiveAToken, address liquidationFeeTo`).

## Results, 7 days to 2026-11-20 05:00Z

| chain | pools / comptrollers the operator took from | new? |
|---|---|---|
| arbitrum | Radiant v1 `0x2032b9a8...` (110 txs), Aave v3, Granary `0x102442a3...` (8), `0xe1ee45db...` (2), three Compound-style singles | Radiant v1: real but dust (below) |
| bsc | Venus core, Kinza `0xcb0620b1...`, Aave v3, Aqualoan `0x75110783...` (52), Cream `0x589de0f0...` (11), three small comptrollers | Aqualoan = flash source only; the rest dust (0.05-2 USD per take) |
| base | Moonwell, Aave v3, Sonne Base `0x1db2466d...` (9), xLend `0x09b11746...` (4), singles | dust (0.2-0.8 mWETH per take) |
| optimism | Aave v4 hub `0x66753c4e...` (EtherFi market), Moonwell, Aave v3, Exactly, Compound v3, Silo v1 ezETH silo `0x12ee4be9...` | all have bots or are dust |
| polygon | Fluid, Aave v2 / v3, Compound v3 | all known |
| avalanche | Aave v2 / v3, Benqi, the drained fork `0xb2e7216f...` | all known |

**Radiant v1 Arbitrum** (protocols row `radiant_v1`): 144 events, 116 users, 137 by the operator. 143 stable-debt covers
sum 115 USD, median 0.51, max 14.66. The pool pays a 15 % bonus but routes 6.52 % of the seized collateral to a fee
receiver, so the liquidator keeps 7.5 %: 8.6 USD for the week (120 events were a three-day backlog sweep), 0.36 USD a
day afterwards, against 0.038 USD of gas per take. The 15 largest takes all landed in the block the position crossed:
nine are same-asset loops (USDC.e against USDC.e and the like) whose health factor drifts down by interest alone
(1.00006 four days before, 1.00001 one day before), six are price moves healthy 3 s earlier. Only 0.3-0.5 USD covers
sit under water for hours. Scripts: `scratch/rf73e/radiant_liq.py`, `windows.py`.

**Aqualoan on BSC** (Aave fork, 11 reserves): the operator uses it as a **zero-premium flash lender**
(tx `0x784f76ff77c7827bec4cf9a42d99eced93a48ec6acf05da1ef6ce087182da87f`: 592.44 USDT out and back, `FlashLoan` log,
the liquidation is on Aave v3). At head 134,634,276 its aTokens hold no cash (0 on 10 reserves, 0.21 USDT), after
bursts of rising-size withdrawals in blocks 133,982,521-133,984,520. Nothing to take and no longer a flash source.
