---
type: infra
chains: [ethereum, arbitrum, base, optimism]
protocols: [across]
author: researcher/opus
updated: 2026-11-14
---
# Bot census: Across SpokePool relayers (op-394311a6 and peers) — class C

**Conclusion:** Across relayers fill cross-chain intents on the destination chain from their own inventory and are repaid on the origin chain (about 98% of fills) after the optimistic bundle. In one 51-minute Ethereum window the top relayer filled 55k USD and booked 45.6 USD of gross spread (8.2 bps), before the LP fee deducted at refund and before gas. Farm can't copy it: it needs inventory on at least two chains plus a way to move repaid funds back (bridging), and open fills are a first-come relayer race (timing wanted). Ledger source `across.filled_relay` was installed 2026-11-14 on ethereum, arbitrum, base and optimism.

## Mechanism
- A depositor calls `deposit` on the origin SpokePool with `inputAmount`. A relayer calls `fillRelay` on the destination SpokePool and sends `outputAmount` to the recipient. `inputAmount - outputAmount` = relayer fee + LP fee. The relayer is refunded `inputAmount - LP fee` on `repaymentChainId` once the HubPool bundle is executed (optimistic, about 1-3 h; not measured here).
- `FilledRelay(bytes32,bytes32,uint256,uint256,uint256,uint256 indexed originChainId,uint256 indexed depositId,uint32,uint32,bytes32,bytes32 indexed relayer,bytes32,bytes32,bytes32,(bytes32,bytes32,uint256,uint8))`, topic0 `0x44b559f101f8fbcc8a0ea43fa91a05a729a5ea6e14a7c75aa750374690137208`.
- SpokePools (verified 2026-11-14: proxy code 680 bytes plus FilledRelay logs): ethereum `0x5c7bcd6e7de5423a257d81b442095a1a6ced35c5`, arbitrum `0xe35e9842fceaca96570b734083f4a58e8f7c5f2a`, base `0x09aea4b2242abc8bb4bb78d537a67a245a7bec64`, optimism `0x6f26bf09b1c792e3228e5467807a900a503c0281`.

## Activity (relay getLogs, 2026-11-14 ~01:15Z)
- ethereum, blocks 26409581-26409881 (300 blocks ≈ 1 h): 274 fills, 12 relayers (0x394311a6 87, 0xfd03abca 61, 0xbdd50e6f 31, 0x07ae8551 27).
- arbitrum, 5,000 blocks (~21 min): 31 fills, 8 relayers. base, 1,800 blocks (1 h): 20 fills, 6 relayers. optimism, 1,800 blocks (1 h): 20 fills, 5 relayers.
- The same relayer addresses appear on every chain (0x394311a6, 0xfd03abca, 0x07ae8551, 0x20c58c01): **multi-chain inventory operators**.

## Economics (ethereum destination, blocks 26409625-26409879, ≈51 min; USDC/USDT/WETH output, BSC origins excluded, ETH = 1,929.50 Chainlink)
| relayer (topic3) | fills | volume USD | gross spread USD | bps | max fill USD |
|---|---|---|---|---|---|
| 0x394311a6 | 42 | 55,393 | 45.55 | 8.2 | 26,451 |
| 0xfd03abca | 31 | 17,869 | 9.98 | 5.6 | 3,189 |
| 0xfd0aa754 | 3 | 5,153 | 7.16 | 13.9 | 3,819 |
| 0x07ae8551 | 12 | 4,526 | 0.85 | 1.9 | 3,956 |
| 0x20c58c01 | 15 | 2,079 | 0.55 | 2.7 | 399 |
| 0xbdd50e6f | 23 | 363 | 0.52 | 14.2 | 109 |
- Total over 138 decoded fills ≈ 68 USD gross spread in the window. **Not net:** the LP fee (paid to HubPool LPs out of the refund) and the fill gas (~0.1 USD at 0.5 gwei) are not subtracted. Repayment chain = origin chain on ~98% (repayment 56: 91, 8453: 64, 4663: 30, 42161: 21, 137: 13, 1: 5).
- Script: `scratch/r4e4f/across_spread.py`, `across_repay.py`; data `scratch/r4e4f/across_eth.json`.

## Operators
- **op-394311a6**: EIP-7702 EOA `0x394311a6aaa0d8e3411d8b62de4578d41322d1bd`, nonce 281,475 (2026-11-14). First funder `0xb5d85cbf7cb3ee0d56b3bb207d5fc4b82f43f511` (0.045 ETH `0xb8cbf90275526c57dcdb22cc1eda680f86b6eeaf3243c183d0958c96a579ee97`, 2025-06-27). Fills send WETH into the SpokePool (69 transfers / 29.4 WETH in 80 min, e.g. `0x28e0ce6eb9f56c1a5f68839817946d845656902e7dc377047792484f5e008464`).
- **op-fd03abca**: relayer contract `0xfd03abcadaf3f930fa4e37eb2f6ea3a44a41b7f0` (18,817 bytes); 56 WETH transfers / 10.39 WETH to the SpokePool in ~95 min (e.g. `0xa8db2a5e830b890215056978c6becf8d30b6d3988e6a059e7af224f123887bad`); its tx_from is not yet traced.
- Both received internal ETH from `0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43` (owner `0x44ae50e8…`), e.g. `0x7dfe5350d628fe7375a02a2696ab45f1e51b49785821b7b9ebed03658f4c7693` and `0xe028287a1b982068554450e8551a4c8530088be53589e71b47a53b890e16ae9e`. That looks like a shared payer (refund or settlement contract), so **not merged**; identity not checked.
- Both also pay USDC/USDT to `0x0f7ae28de1c8532170ad4ee566b5801485c13a0e` (e.g. `0x26b480a0…dabd`, `0xe8d639fe…535d`); probably the recipient side of fills, also not merged.

## Capital, timing, what farm lacks
- Capital: inventory on each destination chain sized to the largest fills (26k USD seen); refunds land on the origin chain about 1-3 h later.
- Timing (measured 2026-11-14, 10 base→ethereum fills from ethereum blocks 26409625-26409879, matched to base `FundsDeposited` by depositId; script `scratch/r4e4f/across_timing.py`): deposit→fill **median 7 s, min 0 s, max 18 s**, i.e. the first or second Ethereum block. 4 of 10 were **exclusive** fills by 0x394311a6 (the deposit names it `exclusiveRelayer`, exclusivity 12-19 s after the deposit: an off-chain quote, e.g. deposit `0xf370e26a72a678edc780980068bb8d653a1351cdbf4f39b23cf9861f2e637c41` → fill `0x771c322ac2804b3ccbb7fb14d228e84f830d64677a856eb22f7b6eec3b834346`, 7 s). 6 were open fills taken 0-18 s after the deposit by 0xbdd50e6f (4), 0x394311a6, 0xfd03abca and 0x6cd1b8cf. So open fills are a first-block relayer race, and exclusive fills are quote flow.
- Farm lacks: (1) inventory on ≥2 chains plus a rebalancing bridge (refunds arrive on the origin chain), (2) principal held for hours outside the bot wallet (the refund isn't in the same tx, so the L rule fails: the fill is not atomic with its repayment), (3) speed for open fills (filled in the first Ethereum block after the deposit), or (4) a relayer quote integration for exclusive fills (off-chain RFQ, private flow).

## Class
**C/D**: even with multi-chain inventory and a bridge (C), the open fills are a first-block race and the exclusive fills are quote flow (D). Not a good weekly-C candidate unless the human wants a quoting-relayer setup. The LP-fee share of the spread is still unmeasured.
