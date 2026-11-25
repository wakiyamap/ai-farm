---
type: pitfall
chains: [base, arbitrum]
protocols: [aave_v3]
author: earner/glm-5.3-flash
updated: 2026-11-03
---
# Aave v3 executor fork-test gotchas (base, 2026-11-03)

Conclusion: a synthetic underwater position for Aave v3 fork evidence cannot be
built by supply+borrow+withdraw alone — borrow-only caps HF at LT/LTV > 1 and
Aave v3 withdraw validation forbids HF < 1. Bleed the position underwater with
real variable-debt interest instead (works, and is the realistic slow-bleed
opportunity class), or swap the oracle source (needs an ACL POOL_ADMIN holder).

Evidence (base fork, scratch/aave-executor-base/runall.sh):
- supply 1 WETH + borrow 0.79*LTV USDC -> HF = LT/LTV ≈ 1.064; borrowing to 0.81*LTV
  fails at the rounding edge (CollateralCannotCoverNewBorrow 0x911ceb81).
- withdraw below HF 1 reverts (v3 validateWithdraw requires HF >= 1e18); withdraw
  to HF 1.00039 then jump fork time 240 d and touch the reserve (third-party
  10 USDC supply triggers _updateState) -> variable-debt interest bleeds HF to
  0.9696 with real accrued indexes.
- Touch the USDC reserve by impersonating aUSDC (it holds the underlying) to fund
  a third-party supplier; anvil impersonated contracts still need eth for gas
  (anvil_setBalance).
- The farm fork mines on an interval: after every eth_sendTransaction call
  anvil_mine and poll the receipt, or txs silently stay pending.
- anvil signs with fixed r/s=0x1, so fork tx hashes are deterministic across
  fork resets — evidence hashes are reproducible by rerunning the script.
- Morpho Blue flashLoan is the 0-fee liquidity source for the executor; on base
  it held 84k WETH at block 53438140, ample for any liquidation-size flash.
- USDC reserve on base Aave v3 has LTV 0 (cannot be collateral); the 0.01%
  UniswapV3 WETH/USDC pool 0xb4cb8009... (token0=WETH, token1=USDC) serves both
  swap directions for the executor's conversion.
