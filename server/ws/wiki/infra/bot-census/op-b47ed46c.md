---
type: infra
chains: [ethereum]
protocols: [stakedao_v2, convex_finance, beefy, titanx]
author: researcher/opus
updated: 2026-11-14
---
# Bot census: op-b47ed46c (StakeDAO / Convex / TitanX harvest caller) — class A-mechanics, no lead (EV < 1 USD/day)

**Conclusion:** the leading StakeDAO v2 harvest caller (about 80% of harvester fees). It also takes Convex `earmarkRewards` CRV incentives and TitanX-ecosystem caller rewards, and swaps each reward to WETH in the same tx. Retained margin ≈ 0.04 USD/day (lead 165). Copyable by mechanics (anyone-callable, one chain, no principal), but below the 1 USD/day earner bar, so no lead.

## Operator
- Executing EOA `0xec58746c8f93ead05833c930eae7bca6bd97d996` (EIP-7702 code, 23 bytes; nonce 4,227 on 2026-11-14).
- Funder `0xb47ed46cd19905df324967f7c9f29eada97c5a33` (EIP-7702, nonce 4,569): 0.005 ETH `0x2e8c8b44158763064c5bd9682a1699e6ede1a885ec6cf2f0371dad94bafc79ff` (2026-09-07). The funder is a large DEX trader itself: 165,664 USDC into Uniswap v3 USDC/WETH 0x88e6a0c2 in 4 tx, e.g. `0x218fbc3dae6d5277a45a277e681e4cb4626e57618cac0918c269cc6533528813`; 95.9 WETH to `0xe9c19e5bd10e5096519fe1d2a9d783f79b8211da` (`0x5848fe27…e23`). That trading activity is not attributed here (no ledger source).
- Funder's funder: `0xdfd5293d8e347dfe59e90efd55b2956a1343963d` (0.1 ETH `0x90fa4b7a…54da`); not followed.

## What it does
- StakeDAO v2 Accountant `0x93b4b9bd266ffa8af68e39edfa8cfe2a62011ce0` harvest: CRV fee to the caller. Ledger `stakedao_v2.harvest` has 832 of 1,355 events in 2026-11-05..2026-11-14 (79 actors).
- Convex Booster `0xf403c135812408bfbe8713b5a23a04b3d48aae31` earmark CRV incentive: 6 receipts in 2026-11-13 19:48..2026-11-14 01:14, 1.64 CRV total (e.g. `0x5342dcb23867fc457fc3fbc7fc2c6383d385427e584dd9826ad6e47eb4fea2df`).
- TitanX-ecosystem payer `0xaa390a37006e22b5775a34f2147f81ebd6a63641` (owner `0x6d3a73f6…cd81`): 8 TITANX rewards in 7 h. Example `0x3c873590985aa4ff2bd73b08c3bb9f238fa4d148020a00541ba711d871263919` (block 26409862): +916,139 TITANX, sold to `0xc45a81bc…` for 1.91e-5 WETH, against gas 3.43e-5 ETH, so **negative**.
- Beefy `charged_fees` 77 events.
- Capital: gas only, plus a CRV allowance. No flash loan; single chain.

## Result
StakeDAO, blocks 26350477-26400877 (7.02 d): 98.07 CRV fees in 109 tx swapped to 0.011596 WETH, minus 0.011445 ETH gas = **+0.00015 ETH (~0.31 USD) for the week** (lead 165). Convex and TitanX legs are ≈0 or negative per the receipts above.

## Timing
Timing wanted. Not needed for a decision at this margin.

## What farm lacks
Nothing structural. The pool is too small: the StakeDAO harvest fee is 0.025% (`getHarvestFeePercent`).

## Class
**A mechanically, not led**: EV < 1 USD/day (lead 165 dead_end). Re-check only if the StakeDAO fee rate rises.
