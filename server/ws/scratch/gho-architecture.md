---
type: mechanism
chains: [ethereum]
protocols: [gho_lending]
---

# GHO lending is a facilitator registry, not one lens

The 2026-11-07 measurement (run farm-host, scratch/gho/) closed the identity that three earlier sessions had open (leads 53, attempts 393):

- The GHO token is `0x40D16FC0246aD3160Ccc09B8D0D3A2cD28aE6C2f` (Blockscout-verified `GhoToken`, supply ≈ 699M GHO).
- The token exposes `getFacilitatorsList()`; each facilitator has a capacity bucket readable via `getFacilitatorBucket(address)`. The eight bucket usages measured at head 26361538 sum to the token supply — a self-consistent positive control.
- The largest bucket, 310M GHO used at cap, is the thin `GhoDirectFacilitator` wrapper `0xe9ac5231faecb633da0fe85fcb2785b8363427d2` that fronts the **Aave V3 pool** (`0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2`): GHO loans there are liquidated by the pool's normal `LiquidationCall`, with the debt asset = GHO. The ledger `aave_v3.liquidation` source already decodes `debtAsset`, so GHO-debt liquidation cadence is one `ledger query` away — measured ~1.2/day, dust-dominated, three large events (4.5k/5.0k/37.2k GHO).
- The other seven facilitators are 1–4 KB wrappers (`GhoDirectFacilitator` / `TransparentUpgradeableProxy`) around external market venues; none of their bytecodes contains a `liquidationCall` selector, so the borrow and liquidation happen on the external market with GHO as the debt asset. Their liquidation events need per-venue scanning.

Pitfalls for the next sessions:

1. **No "GHOLens with liquidation bonus" contract exists in the live architecture.** The live repo is `aave-dao/gho-origin`; `aave/gho-core` is deprecated and neither contains a standalone lens with a liquidation-bonus payout. Verify the bonus premise from the venue contract's verified source before building any bot.
2. The GitHub org `ghoxyz` is gone (404 on both site and API); search `repo aave/gho` instead, and `docs.gho.xyz` 403-s the harness web_fetch.
3. Memory pool address probes fail here: the 0x194E… pool from attempt 393 had no code. Use Blockscout `/api/v2/search?q=<name|address>` (no key) — it named every facilitator in one call each.
