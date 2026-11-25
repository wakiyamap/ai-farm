---
type: infra
chains: [base]
protocols: [morpho_blue]
author: earner/qwen3.8-flash-next
updated: 2026-11-15
---
# op-ed989ee2: ed989 (base morpho_blue, census ranks 5 + 8)

Operator group `ed989` runs two Morpho Blue liquidation executors on base plus one shared settlement swapper:

- executor `0xed989ee258ecc93769a8478c9973667b17462dfe` (census rank 5; crash-window A: 263 events / 249,316 USD nominal gross) - runtime 15,733 bytes, solc 0.8.28 (bytecode CBOR suffix `00081c`, relay `eth_getCode`, scratch/c22ed989/).
- executor `0x91d682699cf4dbfb8a5ea4e860bf29f76ede99cd` (census rank 8; crash-window A: 402 events / 258,369 USD) - runtime 22,750 bytes, solc 0.8.28, 22 dispatcher selectors (regex-extracted from the bytecode).
- shared swapper `0xd1d42cbce8ba22ba2394e37acfc3c97c7457a982` - 24,211 bytes, 36 dispatcher selectors including its own `onMorphoFlashLoan(uint256,bytes)` `0x31f57072`; holds working capital at head: 537,320.05 USDC + 60.0 WETH, 0 ETH (relay `eth_call`/`eth_getBalance`, 2026-11-15).

Both executors share the selector family `atlasSolverCall(address,address,address,uint256,bytes,bytes)` `0x024181a6` + `onMorphoFlashLoan` `0x31f57072` + `pancakeV3SwapCallback(int256,int256,bytes)` `0x23a69e75` + `unlockCallback(bytes)` `0x91dd7346` (Balancer) + `WETH_ADDRESS()` `0x040141e5` = one codebase; `0x91d68269` additionally exposes a direct entry `0x0a05570d`. Verified source not reachable from this host (Blockscout behind Cloudflare per the earlier cards; not re-attempted) - read by trace per decision 2-2 fallback.

Taker type: **O (auction)** for the Atlas captures (`to` = Atlas MetacallRouter `0x583dcfef0d240dc80753f0f0b26513fee27d9b77`, selector `0x4317ca01`, measured `eth_getTransactionByHash` on 0xfcb9aba1 and 0x9a75b0b5) and **B (direct executor)** for the `0x0a05570d` sends from operator EOAs (0x09464a90..., 0xfe5d0060... measured on 0xb5b5c1e4, 0x90e889f8).

## Contract (read 2026-11-15, earner run b4f4a300)

Evidence txs (all base, callTracer via relay research lane, saved under `scratch/c22ed989/`):

- `0xfcb9aba18caccc705a44f6d18bcf1cc82729941a7a1fe87769e27f24c9dd912d` (block 57518827, **39 liquidations in one tx**, 4,193,764 gas = **107.5k/liquidation amortized**, status 1, effectiveGasPrice 15.006 gwei, `tr_atlas39.json`).
- `0xb5b5c1e46615dc76a84afa5ea7ec42c898c4e843fe57474eb36d236a981b2279` (block 57582358, direct entry, 1 liquidation, 2,124,272 gas at 0.115 gwei = 0.24 USD, `tr_direct.json`).
- `0x9a75b0b5acf4ce588af0474b59ee3c23ab5f96e431ff75972defcd993224b178` (block 57581105, `0xed989ee2` via Atlas, 18 events, 5,558,832 gas = 308.8k/liquidation, 15.005 gwei - the older executor batches heavier per position).

- **Entry**: dual. (1) Atlas: router `0x583dcfef` metacall -> executor `atlasSolverCall` `0x024181a6` (same entry as payout51c, card `op-9cbb82b9.md`). (2) Direct: EOA calls the executor itself with selector `0x0a05570d` and a packed job struct (1,668 B for a 1-liquidation job: 52 words carrying the borrower, market id, amounts like `0x87707814` and ~30 embedded token/pool addresses - the candidate set and exit route travel **in the calldata**, nothing market-specific baked in). Who else may call `atlasSolverCall` unprobed on mainnet per 2-5.
- **Funding**: ONE Morpho `flashLoan(address,uint256,bytes)` `0xe0232b42` per batch (zero fee; the 39-event batch: 3,133,118.65 USDC in, repay `transferFrom` 6,428 gas at callback end - frames in `tr_atlas39.json`). The flash loan is SHORTFALL-SIZED: the batch repaid 4,633,882.48 USDC total but borrowed only 3.13M; the swapper covered the 1,500,763.83 USDC rest in-tx.
- **Liquidation loop** (inside `onMorphoFlashLoan`): per position `market(bytes32)` `0x5c60e39a` (1,057 warm) + `position(bytes32,address)` `0x93c52062` (5,045) pre-check, then `liquidate(...)` `0xd8eabcb8` at 35,993 gas warm - the same loop shape as payout51c (card row 6 of `methods/executor-techniques.md`); no standalone `accrueInterest` (Morpho accrues inline).
- **Exit**: NO per-position swap. All seized collateral (898.455 WETH in the 39-event batch, a WETH/USDC-market batch) is forwarded in ONE call to the shared swapper `0xd1d42cbc` selector `0xb9b5f9a2` - 225,466 gas for the whole 39-position batch (~5.8k/position). The swapper is an inventory desk with 537k USDC + 60 WETH working capital at head: it converts the collateral and hands back the flash-repay shortfall in USDC. On the direct path the swapper also runs the route search: `0xedd481bb` (675,721 gas quote, probing ~25 pools/tokens with static `balanceOf`/reserve reads) and executes via `0xc92c9551` (227,201 gas) - the executor holds `pancakeV3SwapCallback`/Balancer `unlockCallback` for its own legs.
- **Profit guard**: no gas accounting inside - no `tx.gasprice`-style read and **zero reads of the OP-stack `GasPriceOracle` 0x420...0f** in either trace (checked all 528 + 975 frames). Same conclusion as payout51c technique row 8: the Atlas path prices gas off-chain in the bid; the direct path relies on the EOA sender picking a cheap fee (0.115 gwei measured).
- **Cheap miss**: unmeasured - no fork resend this session (recorded, not measured). The per-position `market`+`position` pre-checks (6k gas) are where a taken position would be caught; whether the batch skips or reverts is unknown.
- **Priority fee**: Atlas txs effectiveGasPrice 15.005/15.006 gwei (Atlas submitter standard); the direct tx at 0.115 gwei landed 4 minutes after an Atlas sibling (blocks 57581105 vs 57582358) - **same fee environment, 130x cheaper gas price**: the Atlas auction tax is 15 gwei effective, the operator's own direct path pays ~base. No `block.coinbase` payment inside the executor frames in either trace.
- **Batching**: yes - 39 events in one tx (evidence above); also 18 (`0x9a75b0b5`), 16, 11, 5, 3, 2, 1 in the 25 most recent txs (ledger group-by tx_hash, `GROUP BY tx_hash` on `morpho_blue.liquidate`, scratch/c22ed989 session); `0x91d68269` fires bursts of 3-8 txs minutes apart, mixing batch sizes.
- **Where profit stays**: the executors are pipelines - 0 USDC, 0 WETH, 0 ETH at head (relay); in the batch the executor's net is exactly zero (flash in + desk USDC = repay out; all WETH forwarded out). Profit sits at the desk/swapper layer (537k USDC + 60 WETH working capital at head). The Atlas router calls `0x1c6ec84518b859ae6a96c7dd0c78048be7def976` - the same operator wallet d128 and payout51c forward to (`op-d12810b1.md`, `op-9cbb82b9.md`).
- **Gas side-by-side**: 107.5k/liquidation (39-batch) beats payout51c's 129.3k (9-batch) and d128's 123.5k (41-batch) - ed989 is the cheapest per-position batcher of the three read so far on base. Farm comparison unmeasured (no farm executor deployed on base Morpho).

Housekeeping / flaw watch (fork-only rule): standing UNLIMITED USDC -> Morpho allowances on both executors at head (like payout51c's), and additionally `0x91d68269` holds an UNLIMITED USDC allowance toward its own swapper `0xd1d42cbc` (relay `allowance`, 2026-11-15). The swapper is the operator's own contract; recorded, not treated as a drain-path flaw.
