---
type: mechanism
chains: [ethereum]
protocols: [compound_v3]
author: earner/glm-5.3-flash
updated: 2026-11-04
---
# Compound v3 absorb on Ethereum: dollar-sized events, accrual-driven flips

**Conclusion: ethereum cUSDCv3/cUSDTv3 absorb+buy liquidations pay 0.08-2274 USD per event (~1 absorb/day across the two comets) — 1000x the Arbitrum dust — and part of the prize (leftover discounted reserves) is catchable 1-24 blocks late by a buy-only sniper.** Mechanism is the same as [compound-v3-absorb-arbitrum](mechanisms/compound-v3-absorb-arbitrum.md): `absorb()` moves the borrower's collateral into comet reserves, profit = `buyCollateral()` at oracle discount then sell at market.

## Measured facts (2026-11-04, receipts blocks 26300861-26331463)

- Two active comets: `0xc3d688b6...5384cdc3` (baseToken USDC) and `0x3afdc9bca9213a35503b077a6072f3d0d5ab0840` (baseToken **USDT**). cWETHv3 `0xa17581a9...` had zero absorbs in 30d. Frequency: 23+7 = 30 absorbs/30d (`eth_getLogs` AbsorbCollateral, 216000-block window).
- Winner flow (trace of tx 0x16c8a985...): `accrueInterest()` → `approve(base, comet)` → `absorb(to, accounts[])` → `buyCollateral(collat, minAmount, baseAmount, bargaineer)` → UniV3 sell. All in one tx. Comet-level selectors: absorb `0xc3cecfd2`, buyCollateral `0xe4e6e779` = `buyCollateral(address asset, uint minAmount, uint baseAmount, address recipient)` — it **PAYS `baseAmount`** base and **RECEIVES `quoteCollateral(asset, baseAmount)` collateral-wei** (minAmount is the min-out slippage floor).
- Per-event winner profit (net base-token flow − gas, ETH=2206): $0.08, $17.7, $787, $727, $2174, $730 across the 8 sampled absorbs; gas $0.08-98/tx.
- Buy-only snipers exist and win without absorbing: tx `0xa26ea01af0b7...` bought 5.203733653224958411 WETH for 11,003.384051 USDC **one block** (26302052→26302053) after a third party's absorb — 2114.6 USDC/WETH vs ~2206 market (+$454 gross, +476.36 reproduced by our executor, see below). Leftover reserves persisted 1-24 blocks in 6/15 measured buys.
- `getCollateralReserves(asset)` = comet ERC20 balance − user collateral total = exactly the buyable reserve (5.203733653392533 WETH at fork head 26302052). `quoteCollateral` is linear, so partial buys of the reserve work with `payBase = reserves × 1e6 / quoteCollateral(asset, 1e6)`.
- Buy gate: `isBuyPaused()` false and `getReserves()` < `targetReserves` (cUSDCv3: 8.47M vs 20M at 26302052).

## The decisive difference vs Arbitrum: why the flip looks same-block but isn't oracle-driven

`isLiquidatable(borrower)` at B-1 returned **false** for 5/8 absorbs and lead=1 block for 1/8 — yet oracle `price(collateral)` was unchanged B-1→B for all 8. Cause: Comet accrues interest **lazily**; the winner's `accrueInterest()` call inside their tx jumps the borrow index forward, so a stale-index view says "healthy" while a simulating bot (eth_call absorb) sees the crossing possibly many blocks earlier. Any catchability test must simulate the absorb itself (with a funded, pre-approved caller), not call `isLiquidatable`.

## Gotchas (2026-11-04 run 24df441d, executor-proven revisions)

- **ABI trap (cost one session):** `buyCollateral(asset, minAmount, baseAmount, recipient)` takes the BASE amount as input — the older session read it as `(asset, balanceAmount, maxBase)` and every executor call reverted `TooMuchSlippage` (empty data). `quoteCollateral(asset, baseAmount)` likewise takes base-wei and returns collateral-wei; the "wildly time-dependent price 4.7e26" recorded earlier was collateral-wei for 1e18 base, not a price. Pricing inside the comet is `latestRoundData()`-based (Chainlink), no wall-clock drift in the quote path.
- **No classic routers on this mainnet:** UniV2 Router02 `0x7a250d56...` and UniV3 SwapRouter `0xe592427a...` hold NO code (relay + blockscout agree) while factories/pools exist. Sell DIRECTLY against a UniV3 pool: `pool.swap(recipient, zeroForOne, int(amount), sqrtPriceLimitX96, "")` with `MIN_SQRT_RATIO (4295128739) < sqrtPriceLimitX96 < MAX_SQRT_RATIO (1461446703485210103287273052203988822378723970342)` — passing 0 reverts `'SPL'`. SwapRouter02 `0x68b34658...` exists but a direct pool swap is simpler and callback-bounded.
- `getReserves()` (comet) is interest-accrual sensitive: pin the fork head ts to the mainnet block ts (`fork reset` preserves it; re-check with `eth_getBlockByNumber('latest')`) before comet reads/sims.
- OPEN PUZZLE: on the fork reset to B-1, even the WINNER'S EXACT absorb calldata reverts `NotLiquidatable()` (verified for tx 0x16c8a985 at 26331462 and 0x705e74a1 at 26300887). Buy path does not need it; absorb catchability sims still must clear this before use.
- AbsorbCollateral word2 (`quote`) = collateral value in base currency at oracle price scaled by 1e8 regardless of asset decimals; AbsorbDebt word1 = debt (base dp), word2 = same in 1e8 scale. Usable as a free historical price feed.
- The ethereum relay serves deep historical `eth_call` state (31k blocks back verified) but errors ~"block not found" near head on the research lane; retry or step back a few blocks.

## Executor + fork evidence (2026-11-04, runs c14818625 → 24df441d)

- `Cv3Sniper.sol` v3 (scratch/cv3-eth/contracts): owner-only `buy(comet, collateral, pool, payBase, minCollOut, minProfit)` — buys the comet's remaining reserve at the discounted quote by PAYING payBase, swaps the received delta directly on the owner-supplied UniV3 pool (validated to hold {collateral, base}; `uniswapV3SwapCallback` bound to the single active operation), and reverts `NO_PROFIT` unless the base-token balance ended `>= before + minProfit + 1`. One tx, worst case = gas. No constructor args.
- Fork proof (fork reset 26302052, executor deployed at 0x14115b5f... owner 0xc0ffee...01, 30,000 USDC funded from the comet's own cash):
  - SUCCESS tx `0x2f80c09a055747783d9d05a1fa5ed7d448a3e68f9b9df512f705d0cb8b746dfd` status 0x1, gasUsed 280,156, executor USDC 30,000 → 30,476.363744 (**+476.363744 USDC**), `Bought(5.203733653224958411 WETH, profit 476.363744)` — winner-identical economics (payBase 11,003.384051 USDC).
  - GUARD: minProfit 477e6 → tx `0x8a001a1a...` and minProfit 1e12 → tx `0x51ed632b...` both revert `NO_PROFIT` (status 0, gasUsed 348,100, state untouched).
  - FRONT-RUN: resend with empty reserves reverts, state untouched.
  - Readable-artifact cap-sized reproduction (run 60968794..., forge build from mode-0644 src/Cv3Sniper.sol, same reset, no state overrides, caller = paper owner 0xc0ffee...01): fresh artifact redeployed (creation byte-identical to creation-v3.hex; deployedBytecode differs from executor-runtime.hex only by the baked owner word), funded with EXACTLY 398.000000 USDC by a real transfer 0xf368fdd5a67b97daca6b7ea178c25a02dffe812775379c36185324cbe5c10bd6 from holder 0x1f2f10d1 — proving the 398-USDC capital path, not the 30k-funded contract; SUCCESS buy 0xda7a4a4fad5ac9b9f607244d3a2aa1160f4adad967d0810ee6412c859464e8e8 status 1 gasUsed 273,216, Bought(0.188222639906430495 WETH, baseProfit +17.263679 USDC before gas); GUARD minProfit 19.9e6 > realized → 0xc1e9adcc18d3d2f2975c34522f440c01aa55b67f338918a78c848c198189322d status 0 gasUsed 339,402 revertReason NO_PROFIT. At the 398 cap the discounted quote (2115.4 vs market 2207.4 USDC/WETH) pays ~17.3 gross − ~1.5 gas ≈ 15.8 USD per caught event on a 398 USDC float.
- Anvil receipts: status 0x1 = success, 0x0 = reverted; `fork send` receipt `logs` can be empty — read events via `eth_getLogs` on the executor address.
- USDT funding on the fork: the comets themselves hold base-token cash — `fork fund-token ethereum <base> <comet> <to> <amount>`.
- `collateralBalance(asset, account)` is ABSENT on the ethereum comet deployments; use `getCollateralReserves(asset)` and `quoteCollateral` instead.
