---
type: infra
chains: [ethereum]
protocols: [llamaLend]
---
# LlamaLend (Curve crvUSD markets): live stack identified, permissionless liquidations measured

LlamaLend mainnet is the biggest debt book on the farm chains: about **42.9M USD borrowed** on ethereum (DefiLlama `curve-llamalend` "Ethereum-borrowed"; 48 live markets). The 2026-11-06 follow-up (run d12b6409, attempts 330/331) identified the live stack and measured the liquidation class; the earlier scout (run 3ce73b32) had pinned only stale sources.

## Live architecture (all pinned from live sources, not memory)

- Factory: Curve **OneWayLendingFactory for LlamaLend** `0xeA6876DDE9e3467564acBeE1Ed5bac88783205E0` (Blockscout verified name; creation tx `0x2d187c0b61a23da81c648d8b0f0e244b074ab0ab143fc71b7290955e800379f1`, block 19422660; deployer `0xbabe61887f1de2713c6f97e567623453d3C79f67` = "Curve: Deployer 2"). Source header: "Factory of non-rehypothecated lending vaults" - Curve.fi Vyper, `@version 0.3.10`.
- The factory's `market_count()` = **48** markets, enumerated via `controllers(uint256)` (selector `0xe94b0dd2`; the returned 32-byte words hold the address in the trailing 40 characters - a padding trap). Top-20 by debt cover 100 pct of the book (`scratch/llamalend-rolegate/ctrls.json`). Sum `total_debt()` = **42.87M raw** = the DefiLlama borrowed book.
- Each market is a **crvUSDController** (verified source of the deployed proxies): `liquidate(address user, uint256 deadline)` is **permissionless - there is NO liquidator whitelist** on the live controllers. The whitelisted `addLiquidator`/`LiquidatorAdded(address)` design in `LlamaLend/contracts` belongs to the dead NFT-market architecture (its LoanCreated/LoansRepaid topics: zero events in 100k blocks, run 3ce73b32).
- A second llamaLend stack exists - the Solidity 0.8.22 **LoanManager** family (impl `0x553cF903Aace9098684D03C14A5a61610880b72E`): its ABI has `addExecutor`/`executors(address)`/`batchExecute` - liquidations there run through **whitelisted executors**, role-gated and out of scope per `decisions/human/2026-11-06-no-latency-race.md` without measurement.

## Liquidation economics measured (2026-11-06)

- Event `Liquidate(indexed liquidator, indexed user, collateral_received, stablecoin_received, debt)`, topic0 `0x642dd4d37ddd32036b9797cec464c0045dd2118c549066ae6b0f88e32240c2d0`. The first scan of this session returned zero with topic0 `0x642dd4d3`+56 zeros (30 bytes) - see `wiki read pitfalls/relay-getlogs-invalid-params.md`.
- Cadence: **25 events in the last 430k blocks (~28 d) = ~0.9/day** (1,6,2,5,11 per 72k page); lifetime probes found 102 events in the launch window (19422000+) and 22 in 25000000+.
- Sizes: 28-day `stablecoin_received` sum **165,598 USD** repaid; median 403 USD, mean 6,624 USD per event (whale-skewed). `liquidation_discount()` measured live per market: **1.5 - 6 pct** (0.035, 0.04, 0.06, 0.015) - gross per event ~ discount x debt repaid, order 100-300 USD/day before gas.
- Competition: 21 distinct borrowers liquidated by **>=9 distinct liquidator addresses** with no incumbent monopoly (5,5,4,3,2,2,2,1 split); receipts show keepers bidding priority (median 653k gas, effective gas price from 0.03 to 82 gwei) - floor-gas batch gas ~0.2 USD/tx.
- Ledger source `llamalend.liquidate` installed (top-20 market addresses) so future sessions see new events automatically.

Open before any bot (leads:35 next_steps): poll-window probe (how many blocks liquidatable before the capture tx), per-batch net-EV at floor gas, and a per-market collateral sale venue check.
