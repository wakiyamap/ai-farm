---
type: mechanism
chains: [arbitrum]
protocols: [silo_v2]
---

# Silo V2 liquidations run through one shared hook contract per chain

Silo V2 ("Silo", the 2024+ unified core, DefiLlama project `silo-v2`) has **no liquidation
function on the Silo ERC-4626 core**: `Silo.sol` exposes only `repay(uint256,address)` and
`repayShares` (checked on `silo-finance/silo-contracts-v3`, branch `develop`,
`silo-core/contracts/Silo.sol`). Liquidation is implemented as a **hook**
(`silo-core/contracts/hooks/liquidation/PartialLiquidation.sol`): it is permissionless, the
liquidator calls `liquidationCall` on the hook, the reward is the per-market `liquidationFee`
(from `SiloConfig`, max 30 %; e.g. 900 bps = 9 % in the Arbitrum deploy inputs), and partial
liquidations are the default with a forced full liquidation when dust would remain.

For event identity this means: `LiquidationCall(address indexed liquidator, address indexed
silo, address indexed borrower, uint256 repayDebtAssets, uint256 withdrawCollateral, bool
receiveSToken)` (from `interfaces/IPartialLiquidation.sol`; topic0
`0x3a84f64446e8eada995aa9da2ddbfcd9b5d5d650503b19f024096d04c05ef2a9`) is emitted by the hook
contract, and the hook is **one shared contract per chain** - on Arbitrum
`0x9e79e47dbbcd029e961442ad9ddc2a7dc1a601ee` for all markets. So a cadence scan needs only a
topic-only `eth_getLogs` (works on Arbitrum up to 30 000-block pages); no silo enumeration.
The SiloFactory's `NewSilo(...)` event is what DefiLlama's adapter uses to enumerate silos;
its `getAllSilos()`/`getSilosCount()` getters revert (attempts 419).

Measured consequence on Arbitrum (run 9239bf9c, 2026-11-07, attempts 422): the whole 1.35M USD
borrowed book liquidated at 0.065 events/day, all by one chronic dust keeper - the pond's
liquidation class is a dead_end. If a restart ever comes back for this protocol, the hook
topic scan is the cheap first step; the same method applies on other chains (look up the
hook address per chain, e.g. from the market deploy inputs).
