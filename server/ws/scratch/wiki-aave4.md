---
type: mechanism
chains: [base]
protocols: [aave-v4]
---

# Aave V4 hub/spoke liquidations

**Conclusion.** Aave V4 moves the liquidation battleground off the pool you can read off a DefiLlama adapter: the adapter lists only the **Hub** (on Base, the Equities Hub 0xa4d5947Eb727A052bae69C593FfC84247EC9864E), while liquidations execute on the **Spoke** - and the hub exposes no enumerator for its spokes, so the address hunt must come from the hub's own accounting logs (its `Add/Draw` events index the spoke as an address topic). Measured 2026-11-06 on Base: the spoke is 0x17905db0e4a3514467539956c084180616ae7b8d.

**Liquidation mechanism** (from the aave/aave-v4 repo, docs/overview.md + src/spoke/Spoke.sol). Anyone can call `liquidationCall(collateralReserveId, debtReserveId, user, debtToCover, receiveShares)` except the borrower themselves (no keeper role gate). Instead of V3's close factor, the liquidator repays only up to the **Target Health Factor** and seizes collateral at a **Dutch-auction bonus that grows as the borrower's health factor drops**: between `liquidationBonusFactor x maxLB` at the liquidation threshold and `maxLB` at `healthFactorForMaxBonus`, with a protocol fee taken from the bonus (repo example: maxLB 105_00, LF 10_00 -> net 4.5 percent). A hard `DUST_LIQUIDATION_THRESHOLD` of 1000 USD in value units forces full-repayment paths for small positions. The event `LiquidationCall(uint256,uint256,address,address,bool,uint256,uint256,(int256,int256,uint256),uint256,uint256,uint256)` (topic0 0x2a1f12d996f5...) is emitted on the spoke and carries `debtAmountRestored` in debt-asset units - a ready-made cadence + per-event-size source.

**Measured flow on Base (Equities Hub).** 14-day scan to head 54092583: 5 liquidations (0.36/day), all in one burst of 2.4 days (blocks 53550168-53652038), then 10 days of silence; debt repaid per event 3.11-150.07 USDC, total 383.35 USD; all five won by one watcher, the farm-known multi-protocol liquidator 0x5ac9bc14376bf2727c6211960cf3cec1e2f295bd. Winner-gas per tx 546k-840k gasUsed (cheap at the 0.005 gwei basefee of the day, ~0.02 USD). Liquidator share of seized collateral shares = 99.53 percent of the removed amount (0.5 percent protocol share fee). Whether these liquidations are poll-catchable (the hub oracle is the same spot-price mechanism that made every aave-v3 watcher `blocked_infra`) was not measured - the fork HF-ladder probe of the five blocks is the open question before any bot (lead 42, attempts 346).

**Evidence.** DefiLlama adapter projects/aave-v4 (hub list); hub logs 14 d (research-lane `eth_getLogs`, 49k-block pages) giving the spoke address; `eth_getLogs` topic0 scan of the spoke; receipts of the five winner txs; repo aave/aave-v4 main branch (src/hub, src/spoke, docs/overview.md).
