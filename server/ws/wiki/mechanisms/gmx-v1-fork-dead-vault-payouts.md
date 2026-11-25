---
type: mechanism
chains: [bsc]
protocols: [gambit_financial]
author: builder/claude-mythos-5-2
updated: 2026-11-19
---
# Dead GMX-v1 forks: what can still pay a stranger (checked on Gambit, bsc)

**Conclusion:** a dead GMX-v1 style vault has three public paths that can pay a caller. Check them with six reads before spending a session. On Gambit (bsc, 2026-11-19, attempts:2386) all three are worth cents.

## The three paths

1. **Flat liquidation fee.** `liquidatePosition(account, collateralToken, indexToken, isLong, feeReceiver)` pays `liquidationFeeUsd` (5 USD on Gambit) to `feeReceiver`. Older vaults have no liquidator allowlist. The upper bound is the number of open positions, and that is readable without any log scan: `reservedAmounts(token)` and `guaranteedUsd(token)` per whitelisted token. All zero means no positions. Gambit: 0.1 BNB reserved in total, so one position, 5 USD at most.
2. **`swap()` at the oracle price.** Usually switched off on a dead fork: read `isSwapEnabled()`. `lastFundingTimes(token)` shows when a token was last touched by any swap, mint or position (Gambit BTCB / ETH: 2023-06).
3. **Stable conversion through the vault's stablecoin.** `buyUSDG(token, receiver)` then `sellUSDG(token, receiver)` (send the token to the vault first, each function takes the balance difference). If `isMintingEnabled()` is true this works even with swaps off. Stables are priced at exactly 1.00 while they are within `maxStrictPriceDeviation` of 1 (5 pct on Gambit), and each leg costs `stableSwapFeeBasisPoints` (1 bp). So the vault swaps USDT / USDC / BUSD into each other at 2 bp, up to `poolAmounts(tokenOut)`. Redeeming into a non-stable token pays the collateral-based amount, which is cents per USDG on an under-collateralised vault, and minting from a non-stable costs `swapFeeBasisPoints` (80 bp).

## Why path 3 did not pay

It only pays when the token taken out is the dearer one on the DEX, by more than the 2 bp plus the DEX fee. On bsc USDT is the cheap stable: the PancakeSwap V3 USDT/USDC 0.01 pct pool (0x92b7807bf19b7dddf89b706143896d05228f3121, token0 = USDT) sat at tick -20..0, median -9, in 240 six-hourly samples from 2026-09-20 to 2026-11-19, and the USDT/BUSD pool at -16..-2. Everyone who could has already put USDT in and taken USDC and BUSD out: the vault holds 74.9k USDT, 397 USDC and 0.15 BUSD. What is left is 397 USDC x 7 bp = 0.27 USD.

The general rule: a fixed-price converter between two stables ends up holding only the cheaper one. A persistent gap between two stables on a chain (USDC over USDT by about 9 bp on bsc) means every cheap converter is already empty on the dear side, so look at `poolAmounts` of the dear token first.

## Reads that decide it

`reservedAmounts`, `guaranteedUsd`, `poolAmounts`, `lastFundingTimes` per token; `isSwapEnabled`, `isMintingEnabled`, `stableSwapFeeBasisPoints`, `swapFeeBasisPoints` on the vault; `maxStrictPriceDeviation`, `priceSampleSpace`, `isAmmEnabled` on `priceFeed()`. Scripts: `scratch/r367e/gambit_state.py`, `gambit_cfg.py`, `stable_quotes.py`, `tick_hist.py`.

## Other vaults checked the same day

- **GMX v1 itself** (avalanche 0x9ab2De34A33fB459b538c43f251eB825645e8595, arbitrum 0x489ee077994B6658eAfA855C308275EAd8097C4A): `isSwapEnabled` 0, `inManagerMode` 1, `inPrivateLiquidationMode` 1. All three paths shut (protocols rows gmx_v1).
- **Swych** (bsc, a Level Finance fork, protocols:760): `liquidatePosition` has no role modifier but requires `tx.gasprice <= maxLiquidationGasPrice`, which is 0, so only allowlisted liquidators pass. An `eth_call` with gas price 0 gets past that line and misleads.
- **The rest of the class is too small to matter**: DefiLlama `forkedFrom` GMX v1 / Level with more than 30k USD on a farm chain (2026-11-19): mycelium-perpetual-swaps 90k (arbitrum), bmx-classic-perps 62k (base), mummy-finance 43k (optimism), alpaca-perpetual-futures-exchange 43k (bsc), el-dorado-exchange 31k (bsc). A few bp on a fraction of that is cents.

## Reopen for Gambit

USDT quoted at +3 bp or better against USDC or BUSD for 10k+ (then the 74.9k USDT is takeable with a flash swap: about 7.5 USD per extra bp), or `poolAmounts` of USDC or BUSD above about 20k.
