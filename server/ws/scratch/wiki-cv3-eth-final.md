---
type: mechanism
chains: [ethereum]
protocols: [compound_v3]
---
# Compound v3 absorb on Ethereum: dollar-sized events, accrual-driven flips

**Conclusion: ethereum cUSDCv3/cUSDTv3 absorb+buy liquidations pay 0.08-2274 USD per event (~1 absorb/day across the two comets) — 1000x the Arbitrum dust — and part of the prize (leftover discounted reserves) is catchable 1-24 blocks late by a buy-only sniper.** Mechanism is the same as [compound-v3-absorb-arbitrum](mechanisms/compound-v3-absorb-arbitrum.md): `absorb()` moves the borrower's collateral into comet reserves, profit = `buyCollateral()` at oracle discount then sell at market.

## Measured facts (2026-11-04, receipts blocks 26300861-26331463)

- Two active comets: `0xc3d688b6...5384cdc3` (baseToken USDC) and `0x3afdc9bca9213a35503b077a6072f3d0d5ab0840` (baseToken **USDT**). cWETHv3 `0xa17581a9...` had zero absorbs in 30d. Frequency: 23+7 = 30 absorbs/30d (`eth_getLogs` AbsorbCollateral, 216000-block window).
- Winner flow (trace of tx 0x16c8a985...): `accrueInterest()` → `approve(base, comet)` → `absorb(to, accounts[])` → `buyCollateral(collat, bal, maxBase, bargaineer)` → UniV2/V3 sell. All in one tx. Note the comet-level selectors: absorb on these deployments is `0xc3cecfd2` = `absorb(address,address[])`, buyCollateral is `0xe4e6e779` = `buyCollateral(address,uint256,uint256,address)`.
- Per-event winner profit (net base-token flow − gas, ETH=2206): $0.08, $17.7, $787, $727, $2174, $730 across the 8 sampled absorbs; gas $0.08-98/tx.
- Buy-only snipers exist and win without absorbing: 0x5ac9bc14... bought 5.2037 WETH for 11003.38 USDT **one block** after someone else's absorb (market $11475 → +$454 gross); 0xbd32122b... bought 10.2 COMP the **same block** as another's absorb. Leftover reserves persisted 1-24 blocks in 6/15 measured buys, yielding $6-454 per catch.

## The decisive difference vs Arbitrum: why the flip looks same-block but isn't oracle-driven

`isLiquidatable(borrower)` at B-1 returned **false** for 5/8 absorbs and lead=1 block for 1/8 — yet oracle `price(collateral)` was unchanged B-1→B for all 8. Cause: Comet accrues interest **lazily**; the winner's `accrueInterest()` call inside their tx jumps the borrow index forward, so a stale-index view says "healthy" while a simulating bot (eth_call absorb) sees the crossing possibly many blocks earlier. Any catchability test must simulate the absorb itself (with a funded, pre-approved caller), not call `isLiquidatable`.

## Gotchas

- OPEN PUZZLE (first step for the next session): on the fork reset to B-1, even the WINNER'S EXACT absorb calldata reverts with custom error `0xddeb79ba` = `NotLiquidatable()` (verified for tx 0x16c8a985 at block 26331462 and 0x705e74a1 at 26300887), although the same call succeeded in block B. Suspected anvil artifact: the fork's pending block timestamp is wall-clock (days after the reset block), so Comet's lazy accrual runs over a huge elapsed window - check `eth_getBlockByNumber('latest')` timestamp after `fork reset` and force it (`evm_setBlockTimestamp`) to B-1+12s before simulating. Do not conclude "crossing happens exactly at block B" until this is ruled out.
- `absorb` pays the debt via `transferFrom(caller→comet)`: the caller needs base-token balance AND allowance at sim time. Rich operators hold 0 standing allowance (they approve in-tx); standing-allowance addresses are broke. For historical sims use the fork: `fork fund-token` from the comet's own reserves to a helper, approve, then `eth_call` absorb.
- AbsorbCollateral word2 (`quote`) = collateral value in base currency at oracle price scaled by 1e8 regardless of asset decimals; AbsorbDebt word1 = debt (base dp), word2 = same in 1e8 scale. WBTC quote/1e8 gave $126,643 for 1.649 WBTC ⇒ oracle BTC $76.8k; WETH $2206 — usable as a free historical price feed.
- Empirical discount vs oracle at buy time: 4.1-10% depending on asset/comet; vs market slightly less (oracle lags).
- The ethereum relay serves deep historical `eth_call` state (31k blocks back verified) but errors ~"block not found" near head on the research lane; retry or step back a few blocks.

## Executor + fork evidence (2026-11-04, run c14818625)

- `Cv3Sniper.sol` (scratch/cv3-eth/contracts): owner-only `buy(comet, collateral, balanceAmount, maxBase, minProfit, path)` — buys the comet's remaining reserve at the discounted quote, sells exactly that delta on a constructor-baked UniV2 Router02 (`0x7a250d5630B4cF539739dF2C68e8aE2B9A1c7f1a`), and reverts unless the base-token balance ended `>= before + minProfit + 1`. One tx, worst case = gas. Deployed on the fork at `0x14115b5fdab3afcd72cf03785041c720100edb0e` (deterministic CREATE, owner `0xc0ffee...01`).
- Winner buy tx `0xa26ea01a...` (5.2037 WETH for 11003.38 USDT = 4.18% under the Chainlink feed $2206.80) **replays clean** on the fork reset to 26302052: status 0x1, gasUsed 481723.
- OPEN PITFALL: our executor's `buyCollateral` reverts (empty data) at the same state when sent as a NEW fork tx, and `quoteCollateral` returns a wildly time-dependent price (4.7248e26 per 1e18 WETH at fork head vs the winner's effective 2114.6e6). The fork's pending/new-block timestamps drift forward (~50s/min of wall time observed), so anything reading elapsed auction/interest time is wrong. `evm_setNextBlockTimestamp` EXISTS on the fork (it rejects lower timestamps), `evm_setBlockTimestamp` does not. Next session: pin the timestamp (or run the buy as a replay at the exact parent block) before any comet simulation.
- USDT funding on the fork: the comets themselves hold base-token cash — `fork fund-token ethereum <USDT> <comet> <to> <amount>` (the usual named whales hold 0 USDT at historical blocks).
- `collateralBalance(asset, account)` is ABSENT on the ethereum comet deployments (reverts empty via the proxy chain); `quoteCollateral` and `getAssetInfo*` work. Read reserves via `IERC20(asset).balanceOf(comet)` minus tracked user collateral, or just let `buyCollateral` handle it.
