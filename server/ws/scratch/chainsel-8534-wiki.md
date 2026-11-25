---
type: infra
chains: [any]
protocols: [aave_v3]
---
# Chain selection: which new chain to add, Alchemy-supported candidates scored on the human's 5 tests (in progress)

Working table for `decisions/human/2026-11-13-chain-selection.md`. Researchers fill it in across sessions. The final report goes to `inbox/human/<date>-chain-selection.md` (Japanese). Never fill a cell from memory: 未確認 = not measured.

**State after run 8534d4c8 (2026-11-13, researcher-claude):** the candidate list, Alchemy support, DefiLlama borrows and block times are done for every EVM candidate. **Mantle** is the only candidate with test 1 (borrows) and test 2 (blocks >= 2 s) both ○. But its main lender (Aave V3, 110.6M borrowed) paid only **2 liquidations, ~292 USD repaid in 30 d**. So the borrows threshold lets in a chain with almost nothing to take. Every bigger book (Plasma, Monad, Robinhood Chain, Arc, Ink) fails test 2. Among the current farm chains only ethereum and optimism pass test 2.

## Sources (fetched 2026-11-13 ~01:15-01:40Z)

- Alchemy chain list: `https://www.alchemy.com/docs/reference/node-supported-chains` (HTTP URL table).
- Alchemy feature matrix: `https://www.alchemy.com/docs/reference/feature-support-by-chain`. The matrix data is embedded in the HTML (network list + per-method network indices). It is parsed by `scratch/chainsel-8534-feat.py` and gives, per mainnet, `eth_subscribe` / `debug_traceTransaction` / `trace_block`. **Conflict:** the matrix claims trace on polygon and arbitrum and debug on elysium. Farm measurements (TOOLS.md, relay-reference) say no `trace_*` on polygon/hyperevm, arbitrum `trace_block` fails, and elysium refuses debug/trace. For the farm chains, trust the farm measurements. For candidates, the matrix is the only source.
- Borrows: DefiLlama `https://api.llama.fi/protocols`, sum of `chainTvls["<Chain>-borrowed"]` over all protocols (`scratch/chainsel-8534-borrows.py`). Caveat: "Hyperliquid L1" (630.7M) includes Hyperliquid Earn on HyperCore, not only HyperEVM.
- Block time: `(ts(head) - ts(head-2000)) / 2000` through each chain's public RPC (URLs from chainid.network's chainlist, `scratch/chainsel-8534-blocktime.py`). For the farm chains it went through the relay (`scratch/chainsel-8534-farmbt.py`). Heads at ~01:25Z.
- Liquidations: Aave V3 `LiquidationCall` (topic0 0xe413a321...5286) on the Pool from bgd-labs aave-address-book (GitHub raw). 30 d scanned in 10k-block pages through the public RPC (`scratch/chainsel-8534-liqscan.py`). Debt is priced at the Aave oracle at head. Output: `scratch/chainsel-8534-<chain>-aave.json`.

## Candidates (EVM mainnets on Alchemy, not in the farm)

All of them have Alchemy HTTP + WS (`eth_subscribe`) + debug per the matrix, so test 5 is ○ for every one. Trace column: Y/-.

| chain | borrows (DefiLlama) | top 3 lenders | block s (measured) | trace | 1 | 2 | 3 | 4 | 5 | note |
|---|---|---|---|---|---|---|---|---|---|---|
| Plasma | 797.7M | Aave V3 670.1M, Euler V2 104.1M, Fluid 21.6M | 1.000 | Y | ○ (borrows) / × (liq 3.5k USD) | × | 未確認 | ○ (top-1 7/19 events, 37%) | ○ | Aave V3 30 d (blocks 34997061-37589061): 19 LiquidationCall, 3,532 USD repaid, 2 events >= 1k USD, 5 liquidators |
| Monad | 792.4M | Accountable 281.2M, Aave V3 207.3M, Morpho Blue 119.7M | 0.303 | Y | ○ | × | 未確認 | 未確認 | ○ | public RPC: getLogs "block range too large" at 10k |
| Robinhood Chain | 470.6M | Morpho Blue 463.4M, LayerBank 4.5M, Accountable 1.4M | 0.105 | - | ○ (borrows; liq 0.53M < 1M) | × | 未確認 | ○ (top-1 25/160 = 16%, 49 callers) | ○ | Morpho 0x9D53d5E3bd5E8d4Cbfa6DB1ca238AEA02E651010 (Morpho docs addresses page; code 15582 B) blocks 88285349-112971063 (29.6 d): 160 Liquidate, 532,028 USDG repaid (+47.86 SPCX), output scratch/chainsel-8534-robinhood-morpho.json |
| Arc | 274.5M | Morpho Blue 174.5M, Aave V4 100.0M | 未確認 (testnet 0.508) | Y | ○ | 未確認 | 未確認 | 未確認 | ○ | mainnet chainId not in chainlist |
| Mantle | 110.9M | Aave V3 110.6M, Compound V3 0.2M | 2.000 | Y | ○ (borrows) / × (liq 292 USD) | ○ | 未確認 | ○ (2 events, 2 addresses) | ○ | Aave V3 30 d: 2 LiquidationCall, 292 USD |
| Ink | 57.1M | Tydro 57.1M | 1.000 | Y | ○ | × | 未確認 | 未確認 | ○ | |
| X Layer | 49.7M | Aave V3 49.7M | 1.000 | Y | × (0.3M short) | × | 未確認 | 未確認 | ○ | |
| Pharos | 35.8M | Morpho Blue 31.4M | 0.970 | - | × | × | | | ○ | |
| Gnosis | 30.0M | RealT RMM 14.8M, Aave V3 14.5M | 5.075 | Y | × | ○ | | | ○ | |
| Sonic | 26.3M | Euler V2 22.6M | 2.155 | Y | × | ○ | | | ○ | |
| Stable | 24.1M | Morpho Blue 24.1M | 0.699 | - | × | × | | | ○ | |
| Berachain | 13.9M | BEND 8.4M | 2.000 | Y | × | ○ | | | ○ | |
| Katana | 10.8M | Morpho Blue 10.8M | 1.000 | - | × | × | | | ○ | |
| World Chain | 10.7M | Morpho Blue 10.0M | 2.000 | Y | × | ○ | | | ○ | |
| Citrea | 9.2M | Accountable 6.0M, Morpho 3.3M | 未確認 | Y | × | | | | ○ | |
| Sei | 8.4M | YeiLend 5.7M | 0.469 | Y | × | × | | | ○ | |
| Linea | 5.7M | Aave V3 5.2M | 11.104 | Y | × | ○ | | | ○ | |
| MegaETH | 4.7M | Aave V3 4.3M | 1.000 | Y | × | × | | | ○ | |
| Unichain | 1.4M | Euler V2 0.7M | 1.000 | Y | × | × | | | ○ | |
| Tempo | 0.1M | Morpho 0.1M | 0.537 | Y | × | × | | | ○ | |

Below 1M USD borrows on DefiLlama (test 1 ×, not measured further): Celo 1.9M, Frax(tal) 1.6M, Rootstock 1.0M, zkSync 0.9M, Scroll 0.3M, Soneium 0.2M, BOB 0.1M, Mode 0.1M, Boba 0.1M. No DefiLlama borrows: Abstract, ADI, Anime, ApeChain, Astar, CrossFi, DATA Network (Story), Gensyn, Humanity, Jovay, Kaia, Lens, Metis, Mythos, opBNB, Rise, Ronin, Settlus, Shape, Superseed, WorldMobileChain, ZetaChain, Zora (Cronos 0.1M, Injective 5.6M are on Alchemy too). Non-EVM, excluded: Solana, Starknet, Sui, Aptos, Bitcoin, Tron (TVM; DefiLlama JustLend 199.7M), Stellar, and others.

### Current farm chains (comparison)

| chain | borrows (DefiLlama) | block s (relay, 2026-11-13) | Alchemy trace (farm-measured) | 2 |
|---|---|---|---|---|
| ethereum | 19142.5M | 12.036 | yes | ○ |
| base | 2689.8M | 0.200 | yes | × |
| arbitrum | 1076.5M | 0.286 | trace_block fails | × |
| optimism | 86.3M | 2.000 | yes | ○ |
| bsc | 816.8M | 0.451 | yes | × |
| polygon | 73.8M | 1.500 | none | × |
| avalanche | 321.2M | 0.962 | yes | × |
| hyperevm | 630.7M ("Hyperliquid L1", incl. HyperCore Earn 435.0M) | 0.984 | none | × |
| elysium | not on DefiLlama lending | 0.118 | refuses debug/trace | × |

Tests 3 and 4 for the farm chains: use the KB lead rows (e.g. base aave_v3 / morpho, retriage attempts 1059-1077), not yet copied here.

## Threshold notes (for the report)

- **Test 1 on borrows alone is misleading.** Mantle passes on 110.9M borrows, yet Aave V3 there repaid 292 USD in 30 d (blocks 101905038-103201038, 2 events). Plasma Aave V3 (670.1M borrowed) repaid 3,532 USD in 30 d. Large new books are mostly stable/looped positions that rarely liquidate. Suggest scoring test 1 on 30 d liquidation repaid (or both), measured on the main lender.
- **The livest new book measured so far is Robinhood Chain Morpho** (160 liquidations / 0.53M USDG in 29.6 d, 49 callers, top-1 16%: ~150x Plasma's Aave V3 flow). It fails only test 2 (0.105 s blocks) and the 1M repaid line.
- **Test 2 drops every large new book.** Plasma, Monad, Robinhood Chain and Ink are all < 2 s. So are 7 of the 9 current farm chains, including base and arbitrum where the farm already finds its leads.

## Next steps (next session)

1. Monad / Arc (Plasma + Mantle Aave V3 and Robinhood Morpho done): Aave V3 or Morpho; Robinhood: block-gap from oracle update to capture (is it all 0-block?) 30 d liquidation flow and top-1 share (Monad needs a small-range RPC or Alchemy; Robinhood: Morpho Blue address from Morpho docs).
2. Test 3 (SVR / OEV auctions) per candidate main lender: Aave governance SVR rollout per network, Morpho oracle types. All 未確認 now.
3. Arc mainnet chainId + block time from Arc docs. Celo block time (both chainlist RPCs failed).
4. Ordering column (sequencer FCFS vs priority fee) from official docs for Mantle, Plasma, Monad.
5. Then write `inbox/human/<date>-chain-selection.md`.

## Progress log

- 2026-11-12 meta: page created (structure only).
- 2026-11-13 researcher-claude run 8534d4c8: candidate list + Alchemy matrix + borrows + block times for all; Mantle Aave V3 30 d liquidations; Plasma Aave V3 30 d; Robinhood Morpho 29.6 d (see rows). Daily ledger-breadth class not done this run (session spent on chain selection).
