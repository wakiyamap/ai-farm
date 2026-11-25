---
type: infra
chains: [base]
protocols: [morpho_blue]
author: earner/qwen3.8-flash-next
updated: 2026-11-15
---
# op-9cbb82b9: payout51c* base (liquidator census rank 1, base morpho_blue)

Operator executor `0x9cbb82b990ed997d440db1119d07519777c00005` (base): census rank 1 - 1161 morpho_blue liquidation events / 88 txs, 33.4M USD repaid, 1,669,086 USD nominal gross in the frozen cohort (`infra/liquidator-census.md`). Shares the cross-chain payout grouping `payout51c*` (payout wallet `0x51c72848c68a965f66fa7a88855f9f7784502a7f`) with ethereum rank 2 `0xeef1b06e...`, but runs different runtime code (census note). Verified source not reachable from this host (Blockscout API behind Cloudflare "Just a moment"; Routescan "chain not supported"; Etherscan v2 wants a key) - read by trace per decision 2-2 fallback. Runtime 14,187 bytes at head, solc 0.8.27 (bytecode CBOR suffix `00081b`).

Taker type: **O (auction)** - every sampled tx is an Atlas metacall: `to` = MetacallRouter `0x583dcfef0d240dc80753f0f0b26513fee27d9b77`, selector `0x4317ca01`, from the Atlas submitter EOA `0x92e83da3bda8bf72aa855fb587f626d1b2770190` (measured `eth_getTransactionByHash` on 0xb4f85fc3..., scratch/c21r/).

## Contract (read 2026-11-15, earner run 598fdc57)

Evidence tx: `0xb4f85fc3826c88f99fc5f7211e49e92b3942b6c1ab180fc8c9e64318d913ce52` (block 57531655, 9 morpho_blue liquidations in one tx, all in market `0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836` = USDC/cbBTC; repaid 108,004.35 USDC, seized 1.7786 cbBTC per ledger `morpho_blue.liquidate`). Full callTracer via relay: `scratch/c21r/trace_b4f85.json` (104 frames). Selectors confirmed with `cast sig` / `cast 4byte`.

- **Entry**: Atlas router calls the executor's `atlasSolverCall(address,address,address,uint256,bytes,bytes)` (`0x024181a6`), 1,188-byte calldata for 9 positions (~130 B/position). One selector; who else may call it unknown (only observed via Atlas; not probed on mainnet per 2-5).
- **Funding**: ONE Morpho flash loan per batch - `flashLoan(address,uint256,bytes)` `0xe0232b42` on `0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb` for 108,417.58 USDC (zero fee: principal pulled back at the end, 6,428-gas transferFrom), the whole batch runs inside the `onMorphoFlashLoan(uint256,bytes)` callback `0x31f57072`. Contrast: d128 (rank 4) uses Morpho's native repay pull per position with no flash loan (technique row 5).
- **Liquidation loop** (inside the callback): per position `idToMarketParams(bytes32)` `0x2c3c9157` (963 gas warm, 10,963 cold) then `liquidate((address,address,address,address,uint256),address,uint256,uint256,bytes)` `0xd8eabcb8` - 36,054 gas warm, 126,098 for the first. No `accrueInterest` call: Morpho accrues inline in `liquidate`; the executor only re-reads market params. Inside `liquidate`: oracle adapter `price()` -> Chainlink `latestRoundData` (~4,970), seized cbBTC `transfer` to the executor (~4,842), USDC repay `transferFrom` from the executor (6,428 warm).
- **Exit**: NO DEX swap in the capture tx. At the end of the batch the seized cbBTC is pulled to the operator wallet `0x51c72848c68a965f66fa7a88855f9f7784502a7f` (transferFrom 19,732 gas) and that wallet pays the executor 108,417.58 USDC (covers the flash repay) + 2.72 WETH in the same tx. `0x51c72848` is a 23,278-byte contract with ERC-1271 (`isValidSignature(bytes32,bytes)` `0x1626ba7e` with an ecrecover precompile check, 11,316 gas) on the Atlas path - an internal inventory desk, not a pool: price risk and the real exit are off-tx and unmeasured here.
- **Profit guard**: no gas accounting inside the executor found in the trace (no OP-stack `GasPriceOracle` 0x42..0f read, no `tx.gasprice`-style feed call); gas is paid by the Atlas submitter and the Atlas router's `reconcile(uint256)` `0xf68b84f7` is called with -1 at the end (fee handled at the Atlas layer - technique row 1 is the router, not this contract). The executor's own guard shape (min profit?) unknown from the trace.
- **Cheap miss**: untested - the entry is Atlas-gated (bid won off-chain); no fork resend done this session (recorded, not measured).
- **Priority fee**: set by the Atlas EOA (effectiveGasPrice 15.005 gwei at block 57531655); no `block.coinbase` transfer inside the executor.
- **Batching**: yes - 9 in the evidence tx; the ledger shows txs with 30 events (0x001861f7..., 0x9b25f198..., 0x97349577... all n=30); the last 12 txs before it held 1,2,3,3,5,9,9,16,19,30,30,30 events (ledger group-by tx_hash, scratch/c21r).
- **Where profit stays**: swept inside the same tx - WETH `withdraw` (10,163 gas) sends 0.026253 ETH to the executor, which forwards it to `0x1c6ec84518b859ae6a96c7dd0c78048be7def976` (a 335-byte contract - the SAME wallet d128's batch forwards to, `op-d12810b1.md`), and the leftover WETH dust (0.00244) is transferred to `0x51c72848`. At head the executor holds nothing: 0 ETH, 0 WETH, 0 cbBTC, 0.42 USDC (relay `eth_call`/`eth_getBalance`, 2026-11-15).
- **Gas side-by-side**: 1,163,353 gas total = **129.3k gas per liquidation amortized** (9 in the batch) at 15.005 gwei = 0.01746 ETH per batch (receipt math) against ~4-5k USD nominal gross - gas is noise for this operator. Farm comparison unmeasured (no farm executor deployed on base Morpho).

Housekeeping / flaw watch (fork-only rule, not used on mainnet): a persistent UNLIMITED USDC->Morpho allowance sits on the executor at head (`allowance` = 2^256-1, relay `eth_call`) - their standing approval, harmless while Morpho is trusted; recorded, not treated as a drain-path flaw.
