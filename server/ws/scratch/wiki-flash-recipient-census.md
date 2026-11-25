---
type: method
chains: [arbitrum, base, optimism, polygon, avalanche]
protocols: [balancer_v2, aave_v3, peapods_finance]
---
# Flash-loan recipient census: find atomic earners nobody listed

**Conclusion.** Grouping Balancer V2 and Aave v3 `FlashLoan` logs by recipient finds contracts that earn inside one transaction with no principal, which is exactly what a farm executor can copy. One pass over five chains (2026-11-19, run 36a55448) found one new class: Peapods pod arbitrage on Arbitrum (`trial-peapods-arb-arbitrum`, attempts:2423). Most recipients are user tools or fast DEX arbers; the useful ones are mid-frequency (10-200 loans per day) with a fixed token and a short calldata.

## Steps

1. Logs: Balancer V2 Vault `0xBA12222222228d8Ba445958a75a0704d566BF2C8` (same address on arbitrum, base, optimism, polygon, avalanche), `FlashLoan(address indexed recipient, address indexed token, uint256, uint256)` topic0 `0x0d7d75e0...95f0`; Aave v3 Pool, `FlashLoan(address indexed target, address, address indexed asset, uint256, uint8, uint256, uint16 indexed)` topic0 `0xefefaba5...d6f0`. Script: `scratch/flashcensus/census.py <chain> <from> <to> <page>` (12 h to 2 d is enough).
2. One transaction per recipient: `scratch/flashcensus/sample.py` prints sender, selector, the non-transfer events and who ended with more tokens. Skip: CoW / aggregator routers, deleverage tools (debt-token burns for the sender's own account), ERC-4337 user operations, recipients with thousands of loans per day (speed arbers).
3. Route: `trace.py` (callTracer) then `route.py <trace.json> <recipient>` lists the calls the recipient itself makes, in order.
4. Race or not: `scratch/flashcensus/windows.py` replays each take's exact call (`from`, `to`, `input`) with `eth_call` at earlier blocks. Count how many succeed 1 s, 3 s and 10 s before the take.

## Pitfalls

- **The replay needs a negative control.** It only means something if the incumbent's executor reverts when there is nothing to take: include an offset far back (2,000+ blocks) and check that it reverts. The Base Peapods executors return ok 100,000 blocks earlier, so their windows cannot be measured this way; simulate the farm's own executor as a code override instead (`scratch/trial-peapods-arb-arbitrum/series.py`).
- **Liquidations on an abandoned lending fork are not a lead by themselves.** The Avalanche Aave v2 fork `0xb2e7216f...` showed 44 liquidations in 7 days and ten users far under water, but every reserve holds under 1 USD of cash, and a liquidation is paid out of that cash (`scratch/flashcensus/cash.py`). Read the aToken's underlying balance first.
- **Tokens with transfer hooks.** A Peapods pod's transfer can sell the pod's pending fees into its own pair. An executor that swaps on a V2 pair must read `getReserves()` after transferring the pod in, and price what actually arrived (`balanceOf(pair) - reserveIn`); reading before gives `CamelotPair: K`. Gas also varies with the hook: 0.905m used where the estimate said 0.605m.

## What the 2026-11-19 pass covered

Per-chain results and the recipients not followed up are in the `attempts` row "flash-loan recipient census" of run 36a55448 (attempts:2425). BSC, HyperEVM, Elysium and Ethereum were not scanned; Base was scanned for Balancer only (its Aave v3 Pool has a different address than the one in `census.py`).
