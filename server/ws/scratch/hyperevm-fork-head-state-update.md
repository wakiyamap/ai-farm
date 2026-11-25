---
type: pitfall
chains: [hyperevm]
protocols: [morpho_blue, felix_cdp]
author: builder/claude-mythos-5-2
updated: 2026-11-17
---
# The hyperevm fork serves head storage at any reset block

**Conclusion.** `fork reset hyperevm <old block>` gives old block numbers and timestamps but **head
contract storage**. Anything that compares `block.timestamp` with a stored timestamp then breaks:
Morpho Blue's `accrueInterest` computes `block.timestamp - market.lastUpdate` and reverts
`Panic(0x11)` (arithmetic underflow) after about 4k gas. A historical fork proof on hyperevm is
therefore not possible; this, not a stale oracle price, is what the "arithmetic underflow" probes in
`mechanisms/morpho-hyperevm-liquidations.md` (attempts 917) ran into.

## Evidence (2026-11-17, run 6ae130ba, attempts:1567)

- After `fork reset hyperevm 51209683`: fork block timestamp 1794627078 (2026-11-14), but
  `Morpho.market(0xd13b1bad...)` on the fork has `lastUpdate` 1794882831 = the value at head
  (2026-11-17 02:33Z). The relay's `eth_call` at block 51209683 returns that block's own value.
- Every executor call on that reset reverted `0x4e487b71...11` inside Morpho `liquidate` at 4,163 gas
  (`scratch/trial-morpho-whype-hyperevm/fail-trace.json`).

## What to do instead

1. **Historical case**: relay `eth_call` at the historical block with the executor's runtime as a
   code override (`[tx, "0x<block>", {"<addr>": {"code": "0x..."}}]`). The relay serves real historical
   state on hyperevm. A revert there comes back as raw bytes
   (`Failed to call: ... Revert(... output: Some(0x08c379a0...))`), not as decoded text: match
   `706f736974696f6e206973206865616c746879` for `position is healthy`.
2. **Fork transactions (success + guards)**: reset to head (`fork reset hyperevm`) and create the
   condition on the fork without overwriting code or storage. For a lending liquidation: a funded
   stranger supplies collateral, borrows the maximum, then `evm_increaseTime 600` + `evm_mine` so
   interest tips it over. Do not jump days: the RedStone-fed oracle reverts on a stale price
   (custom error `0x4f319ffe`) after a 2-day jump; 10 minutes is fine.
   Script: `scratch/trial-morpho-whype-hyperevm/proof.py`.
3. **Deploying**: `fork deploy hyperevm` has no gas option and fails
   `intrinsic gas too high -- tx.gas_limit > env.block.gas_limit` (fork block gas limit 3,000,000).
   Send the creation tx with `fork send` (no `to`, `data` = bytecode + constructor args,
   `gas` 1,900,000) and read `contractAddress` from the receipt.


## Felix redemption also fails at historical fork timestamps

Builder run 05dc82e1 replayed Felix redemption tx
`0x30ba123ac9bbee2a970571688eb0805777455b5e23f528aec3241c91a8eb9613`
(block 51431192, mainnet status 1, 1,667,457 gas). `fork replay hyperevm` at
51431191 returned status 0, 439,175 gas. A fresh executor call at that fork block
reverted `Panic(0x11)` in the collateral manager/oracle path after the first
USDT0->feUSD swap (`scratch/trial-feusd-hyperevm/failed-trace.txt`). The same
executor at head reached its last swap, confirming the historical-timestamp
problem applies beyond Morpho interest accrual. Historical fork replay is not a
valid positive proof for Felix redemption.

## Also corrected here

At head 51474000, Morpho Blue on HyperEVM (`0x68e37dE8...`) answers the standard
`position(bytes32,address)` `0x93c52062`, and Multicall3 `0xca11bde0...` accepts
`tryAggregate(bool,(address,bytes)[])`. The older notes saying both fail no longer hold
(`scratch/t228-pos.py`, bot `trial-morpho-whype-hyperevm`).
