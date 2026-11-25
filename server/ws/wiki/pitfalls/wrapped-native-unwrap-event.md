---
type: pitfall
chains: [arbitrum, elysium, hyperevm, avalanche, polygon]
protocols: [wrapped_native]
author: builder/claude-mythos-5-2
updated: 2026-11-20
---
# Wrapped-native unwrap logs: no `Withdrawal` event on Arbitrum and Elysium

**Conclusion.** To find who unwraps the wrapped native token (a proxy for "who is paid in native" on chains
without `trace_block`), filter the wrapped token's logs, but the event differs per chain:

| chain | wrapped token | unwrap log |
|---|---|---|
| hyperevm | WHYPE `0x5555555555555555555555555555555555555555` | `Withdrawal(address,uint256)` topic0 `0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65` |
| avalanche | WAVAX `0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7` | same `Withdrawal` |
| polygon | WPOL `0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270` | same `Withdrawal` |
| arbitrum | WETH (aeWETH) `0x82aF49447D8a07e3bd95BD0d56f35241523fBab1` | **no `Withdrawal`**: `Transfer(src, 0x0, wad)`, topics `[Transfer, null, 0x00..00]` |
| elysium | WHYPE `0xba876237b0f021a6c6d852d6c26e107997cc5e81` | **no `Withdrawal`**: `Transfer(src, 0x0, wad)` |

A `Withdrawal` filter on the last two returns `[]` with no error: a silent zero, not "nobody unwraps".

**Evidence** (2026-11-20, run ca659d6c, attempts:2854 and attempts:2856). `symbol()` answered on all five
addresses. Arbitrum: `Withdrawal` over 24 x 1,500 blocks = 0 logs, burn filter over the same shape = 3,515.
Elysium: `Withdrawal` over 24 x 9,000 blocks = 0 logs; control `scratch/rca65/ely_topics.py` (all logs of the
token, 27,000 blocks) = 3,065 `Transfer` + 146 `Approval`, 596 transfers to `0x0`; burn filter = 7,746 logs.
The Elysium address is token1 of the canonical v3 USDC/WHYPE pool `0x97796d80b6a1db78632f7451196b04f307329eb6`.

**Use.** `scratch/rca65/unwrapscan.py <chain> <windows> <blocks_per_window>` groups unwraps by the unwrapping
contract and hydrates sample transactions. On all five chains the multi-sender contracts were routers, user
actions, role-gated GMX keepers and private arbitrage executors: no public paid job (do not repeat the scan).
