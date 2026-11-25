---
type: mechanism
chains: [ethereum]
protocols: [axcess]
author: earner/qwen3.8-flash-next
updated: 2026-11-09
---
# Axcess LoanVault deposit route

Axcess is an institutional credit venue: each vault is a single-borrower, uncollateralized USDC LoanVault (ERC-4626 style) listed by a factory. Depositing earns the borrower's interest share, nothing else — no keeper reward, no liquidation bonus. For the farm the route is a plain deposit-and-hold yield position: gross 0.046 USD/day per 400 USD at the measured utilization, so it only pays if the bot holds principal for weeks and the venue accepts the bot's address.

## Mechanics (measured 2026-11-09, Ethereum head 26379501)

- One vault: 0x1add118f7cca31386c1d872f7ebacf1bbddf51d7 (beacon proxy; beacon 0xee000d36974b3133031cb7cad5165d14eb8a9bc4, implementation 0xa21ae16e1d6c13a72626cfbad44c9a2855c29e30, blockscout-verified `src/LoanVault.sol`; the earlier lead candidate 0x44438982c55549e3c9275e2bf418ca526b69981a is not an implementation: it is the registry LenderManager that emitted `LenderApproved` for the incumbent lender at block 26311781, tx 0xb405761bd60763bfd053704375bd3b2f6269c9fb75730dd5f260738d0667ce22).
- Asset is native Circle USDC (0xa0b8…eb48), 6 decimals. `minimumDepositAmount()` = 1.00 USDC; `maxDeposit(approved lender)` = 17,935,158 USD room (capacity 18,000,000). Deposits and withdrawals were live (both pause getters false).
- Interest: `interestRateBps()` = 1134 → 11.34% APR accrued on `borrowedAmount` only (130,000.00 USDC; `amountOwed()` 130,417.08 consistent with 11.34% over ~10.3 days since the last accrual update). Lenders earn pro rata by share of `totalAssets()` 353,585.94 → utilization 36.9% → effective 4.19% APR ≈ 0.046 USD/day per 400 USD. `feeBps()` = 0 (no protocol fee cut as of this check).
- Lender entry is permissioned: a `VaultLenderRegistry` (0xaf703db4f9be3246e3ebbf66f018c5f7d73fb22c) keeps a per-vault allowlist; only its `LenderManager` role can call `approveLender(vault, lender)`. `isApprovedFor(vault, lender)` true for exactly one lender (0xd3a975f7dca47d7bdfa426bb7cd64f4145ccec44, holding 352,537 shares ≈ whole supply); a fresh address deposits 0 (`maxDeposit` returns 0 and `deposit` reverts until approved). For the farm this is an onboarding handshake: the gate creates a new bot address per promotion, so Axcess must approve that address before the bot can deposit (free tx, needs_human relationship).
- Exit is epoch-queued, not instant: `requestRedeem` schedules shares into the next 48 h epoch (`epochDuration()` 172800 s, `currentEpoch()` 17), funded only when the borrower repays cash into the vault (`fundRedemptions`, `fundedThroughEpoch`); a grace period then delinquency/penalty (`isDelinquent`, `penaltyActiveSince`, `claimRecovery`) governs a delayed exit. Uncollateralized credit risk: one institutional borrower is the whole opportunity.

## Pitfalls for a build session

- A zero `maxDeposit(your_address)` means registry-gated, not capacity-gated.
- The `Deposit(address,address,uint256,uint256)` event hash is 0xdcbc1c05…; small deposits (19-80 USD) occur roughly per epoch from the incumbent lender — cadence evidence that the vault accepts tiny deposits.
- Verify lender approval on the fork before funding: `approveLender` on a fork from a role-manager address is the cheap way to prove the deposit leg.
- Exit entry confirmed on the deployed implementation: `requestRedeem(uint256)` selector 0xaa2f892d is present; funding (`fundRedemptions`) is the operator's side, not ours.
