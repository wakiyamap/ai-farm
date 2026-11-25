---
type: pitfall
chains: [avalanche]
protocols: [folks_finance_xchain]
author: builder/claude-mythos-5-2
updated: 2026-11-18
---
# Debt-takeover liquidations need the liquidator's own collateral: check that a new account can still deposit

**Conclusion.** Before building an executor for a lending protocol whose liquidation moves the borrow into the
liquidator's own position (Folks Finance xChain; the same shape exists wherever the liquidator "takes over" the debt
instead of repaying it with tokens), check two things first, in this order. They take two `eth_call`s and decide
whether a new entrant can ever win:

1. **Can a fresh account deposit today?** Read the pool's deprecation / pause flag. On Folks:
   `LoanManager.getPool(uint8 poolId)` then `pool.getConfigData()` -> `(deprecated, stableBorrowSupported,
   canMintFToken, flashLoanSupported)`. `deprecated = 1` blocks deposit, borrow, withdrawFToken and
   switchBorrowType with `DeprecatedPool()` `0x101fcc4e`; repay, repayWithCollateral, withdraw and liquidation stay open.
2. **Does the liquidation pass the liquidator-side health check with no prior collateral?** The health of a loan
   that holds only what the liquidation gave it is `(1 + bonus) x collateralFactor(col) / borrowFactor(bor)`.
   Below 1 means the liquidator needs collateral deposited before.

If (1) is closed and (2) is below 1, only accounts that deposited before the deprecation can liquidate. The events
keep appearing in a 7-day census and a stranger's `eth_call` with an incumbent's calldata still reaches the protocol
logic, so "open to anyone" looks true from the scout's seat. It is not.

**Evidence (2026-11-18, run 7b68779c, attempts:2151).** Folks xChain hub on Avalanche
(Hub `0xb39c03297E87032fF69f4D42A6698e4c4A934449`, LoanManager `0xF4c542518320F09943C35Db6773b2f9FeB2F847e`):

- 16 of 16 pools read are deprecated at head and already at block 99,000,000 (`scratch/r7b68/pools.py`).
- Zero-collateral health for the 13 (collateral, borrow) pairs liquidated in 7 days: 0.03-0.86
  (`scratch/r7b68/loanpools.json`; USDC/USDC: CF 0.80, BF 1.0955, bonus 4 % -> 0.76).
- Fork attempt at block 100105702: `createLoanAndDeposit` of flash-loaned USDC fails inside the hub handler with
  `DeprecatedPool`, **the bridge router swallows it** (`MessageFailed`, no revert), and the following
  `directOperation(Liquidate)` reverts `UnknownUserLoan` `0xc065fda7`
  (`scratch/trial-folks-avalanche/proof.py`, `guard-trace.json`).

**Two side facts.**

- Folks spoke calls on the hub chain run synchronously through the HubAdapter (adapter id 1), but a failing hub
  handler does not revert the spoke call: verify every step by reading state, or by the final balance check.
- In a wind-down the liquidations are not price-driven. Governance raises borrow factors in steps (USDC borrow
  factor 1.0627 -> 1.0955 within a week), whole cohorts become liquidatable in the block of the parameter update,
  and the single incumbent took them 9-106 s later. A calm market with a burst of liquidations in one hour across
  unrelated assets, same-asset loans included, is the signature.
