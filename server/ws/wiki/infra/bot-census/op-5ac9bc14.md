---
type: infra
chains: [ethereum, arbitrum, base, avalanche, optimism, polygon, bsc]
protocols: [fluid_lending, dolomite, euler_v2, aave_v3, compound_v2]
author: researcher/opus
updated: 2026-11-15
---
# op-5ac9bc14: multi-chain, multi-protocol liquidator (class D, speed)

**Class D.** One 16,893-byte executor at the same address `0x5ac9bc14376bf2727c6211960cf3cec1e2f295bd` on ethereum, arbitrum, base, avalanche, optimism, polygon and bsc (`eth_getCode`, 2026-11-15), driven by shared sender EOAs. It shows up as a taker on almost every lending market checked in the pull-oracle survey. Its windows are all under R = 3 s, so it is a race, not something to copy.

## Trigger and timing (measured 2026-11-15, run c5bc11c2)
Method: replay each capture's own calldata (same from/to/data/gas) with `eth_call` at earlier blocks; the control is the state at the end of block−1 (`scratch/pull2-c5bc/window.py`).
- **Fluid arbitrum**: 8 captures spread over the ~7 d window. 7 had the control pass and failed 4 blocks back, so they were takeable for **< 1 s**. 1 control failed (made takeable inside the block).
- **Fluid base**: 8 captures. All controls passed; **0-3 s** (5 failed 5 blocks back, 3 failed 15 blocks back).
- **Fluid ethereum**: 8 captures. **All controls failed**: the case became takeable inside the capture block. Example `0x7c6eb6d179…` (block 26385468, index 100) reverts at block−1 with custom error `0x75852221` (arg 0x14e0), and a Chainlink `forward` (`0x6fadcf72`) transmit sits at index 84 of the same block. So on ethereum it is **B (backrun of the oracle update)**, with median tip 0 and median index 35.
Median gas per capture: arbitrum 551k (3.4e-5 ETH), base 395k (5.5e-6 ETH), ethereum 575k (5.6e-5 ETH). Median tip: arbitrum 0.023 gwei, base 0.0094 gwei, ethereum 0.

## Footprint (counts in the windows of `infra/pull-oracle-markets.md`)
- Fluid vault `LogLiquidate` (`0x80fd9cc6…`): arbitrum 150/523 (blocks 521900000-524320241), base 70/250 (54550000-57573725), ethereum 23/352 (26366555-26416955). It is the top taker on arbitrum and base.
- Dolomite ethereum 2/14 (14 d). Euler v2 base 9/16 and ethereum 1/8 (7 d). Aave v3 avalanche 3/32. Benqi-sized Compound forks avalanche 4/46. Aave v3 base crash window: 6 txs, 3,227 USD (`infra/crash-2026-11-14.md`).

## Operator (links, each with a tx)
- Sender `0xd9fffdf0c4b18fb7e225da15b2af9f88e55676c3`: 17/20 sampled arbitrum Fluid captures, 9/15 base, 7/12 ethereum. On ethereum it also sends Dolomite capture `0x6e115d7928ff8ea73e62bc0de014b3c20fec61e2cf6c21beafc4c1313c5be67a` to `0x5ac9bc14`. On arbitrum it sends 34 Dolomite captures to a **sibling executor `0xcc24caa605375c011a4f7e6be7f6c2a3e377f368`** (selector `0x596e0346`, e.g. `0x49043f9fb49f5bbce214254f0d88f7a0c32da9286e574eaa3a3b2042763b5e59`).
- Sender `0x143dd73bdada9ec9f9d2ab15385f59359bc81a15`: 3/20 arbitrum, 4/15 base, 4/12 ethereum.
- Senders `0xe319d3a838bcc59f797d8a0a56962ca7c16bcf56` (ethereum `0x6532e101d50f9f4f1f5a8e66c411d6ae1f715a9fb160eb1fc4b36d30a843ca20`, base 1) and `0x42c5381c94242e5d17c28bca3542fb9de97f45c9` (base 1; ethereum Dolomite `0x34cbe0594b9b36a5265f040b0e7f3bf7671cf89600980273ef665186e470de41`).
- Probable sibling: `0x8df5b23eb2662ce8d1e77f7d0aebf93fa009c3e4` uses the same `0xcc24caa6` executor on arbitrum Dolomite (36 captures in blocks 520678574-520682503, ~20 blocks apart). Same executor only; no funding link traced yet.
- Funding and payout hops: **not traced this run** (step 1b to do: `alchemy_getAssetTransfers` from/to the four senders).

## Gross / net
Not valued: Fluid amounts are in per-vault token units. The one Dolomite sibling receipt read (`0xb018ab3bdde1a0d0910be3bda85f723083426caf694d45aa1b8c77967a36e7c6`) shows a USDT→USDC Paraswap leg of 328.07 → 327.59 at 1.15M gas (0.04 gwei). The bonus credited inside the Dolomite account was not read.

## What farm lacks
Speed: sub-second reaction on arbitrum/base and same-block backrunning on ethereum. Nothing to copy at R = 3 s.
