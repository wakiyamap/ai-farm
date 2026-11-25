---
type: mechanism
chains: [base]
protocols: [40acres]
---

# 40acres loans: self-repaying, non-liquidating

**Conclusion.** 40acres on Base is a big lending book (5.51M USD borrowed measured 2026-11-06) that pays **nothing to a liquidation farmer**: its loans are advertised and built as *self-repaying, non-liquidating*. There is no liquidate function in any deployed facet or in the Loan/Vault sources, so liquidation farming has zero EV here (attempts 345, dead_end 2026-11-06).

**Mechanism.** A user locks AERO into the Aerodrome veAERO escrow (or veVELO/vePHAR/veBLACK elsewhere); every portfolio is a diamond-proxy account deployed by the PortfolioManager (0x40Ac2e40ACb7bdD6EC83E468143262fe216529ec on Base). Against the locked veNFT the account *borrows USDC from a supply vault* (`LendingFacet.borrow`, vault.asset() = USDC). Each weekly epoch a relayer calls `LoanV2.claim(tokenId, fees, tokens, tradeData, allocations)`: it claims the veNFT's fee rewards through the voter, swaps them to USDC via ODOS (the swap calldata is supplied by the caller), takes the protocol fee and the lender premium, and repays the loan from the rewards ("Each week the veNFT rewards are used to repay the loan automatically" - repo README). Surplus rewards increase the lock or go to the loan owner. Repay itself is `pay(tokenId, amount)` - anyone can call it, but the protocol pays them nothing.

**Consequences for the farm.** If a borrower's rewards stop covering the debt, nothing gets seized: the account is stuck (collateral requirements are enforced on user actions, `enforceCollateralRequirements`), not liquidated. The veNFT+debt can be sold on the native marketplace (`MarketplaceFacet`, "leveraged buyouts of veNFTs using flash loans") - that is a user trade with inventory risk, not a public bounty.

**Evidence.** Protocol identity and description from the DefiLlama 40-acres protocol page (40acres.finance, org 40-Acres); repo 40-Acres/loan-contracts (main, fetched 2026-11-06): Loan.sol, LoanV2.sol, Vault.sol, VaultV2.sol, LoanStorage.sol contain zero occurrences of "liquidat"; README facet tables list LendingFacet {borrow, pay, setTopUp, topUp} with no liquidate. Live reads (Base head 54089804, relay research lane): Loan proxy 0x87f18b377e625b62c708D5f6EA96EC193558EFD0 `activeAssets()` = 5,508,328.68 USDC borrowed; supply vault 0xb99b6df96d4d5448cc0a5b3e0ef7896df9507c5 `asset()` = USDC 0x833589fcd6edb6e08f4c7c32d4f71b54bda02913. 7-day eth_getLogs 53787404-54089804 over the Loan proxy, vault and PortfolioManager: 181 logs, top topics: LoanPaid 14 (topic0 0x74d71c8dada9ce, ~2/day), vault Transfer 73, two vault fee topics 31+16, PortfolioManager 41+1 - no liquidation-family topic0. Prod addresses match repo addresses/base/aerodrome.json.
