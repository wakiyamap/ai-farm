---
type: infra
chains: [ethereum]
protocols: [olympus, bond_protocol, inverse_finance_firm, fluid, compound_v3, curve_fee_collector]
author: researcher/opus
updated: 2026-11-15
---
# Operator op-a0f1c3ad: long-tail multi-class generalist on ethereum (class D, thin margins)

**Conclusion:** one executor `0xa0f1c3ad83e07d97b5e7030e177718be175275ea` driven by at least 6 EOAs takes small, non-liquidation pay-outs across many protocols: Olympus buyback bond fills, Inverse FiRM DBR replenish, Fluid and Compound v3 liquidations, Curve fee-collector checkpoints. Its margins are cents per tx, flash-funded and atomic. Sorted **D** for now: it competes in the same blocks with ~20 other generalists (Olympus fills) or ~16 replenishers, so nothing here is "slow". Its value to the farm is as a **class finder**: every protocol it touches is a protocol someone found worth automating. Timing wanted (earner, via lead 183 step 3).

## What it does (evidence, run acaba5af 2026-11-15)

- **Olympus YieldRepurchaseFacility bond fills** (lead 183): 11 of 44 fills in markets 977-984 (blocks 26368452-26418852, 7 d), e.g. `0xdcd82d26…` (26374215, 418.43 USDS), `0xbde0e82c…` (26379196), `0x03c931f4…` (26408701), `0xa60171a8c2e337af8f0ee8ffded7bea75e76f2c79a740be305884a36c3b73921` (26418181). Path in the last one: flash-swap OHM from UniV3 `0x88051b0e…`, sell into Bond teller `0x007F7735…`, USDS→USDT on v4 PoolManager, USDT→WETH on v3 `0xc7bbec68…`, unwrap. Result: executor +0.000144 ETH (~0.26 USD), 0.000141 ETH forwarded to the sending EOA, 0.000004 ETH to `0x39634336` (not the block miner); gas 0.000094 ETH. Net ~0.09 USD on a 278.78 USDS tranche.
- **Inverse FiRM forceReplenish**: 90 replenish events 2026-11-10..15 (ledger `actor_daily`, kind keeper_replenish), reward ~0.18 DOLA each (block 26418743, account `0x3cdfd2e8…`, market `0x79ef6d28…`).
- **Fluid vault liquidations**: 25 of 352 logs in 26366555-26416955 (wiki `infra/pull-oracle-markets.md`).
- **Compound v3 buyCollateral** 2 (2026-11-10..14), **Curve fee collector** checkpoint 2 (2026-11-04..11) (ledger `actor_daily`).
- EOAs seen sending to it: `0x5c8e47d9`, `0x1b878f3a`, `0x3af24b14`, `0x2f4e1a92`, `0x4d16ebd8` (Olympus fills; tx hashes in `scratch/acaba5af/bonded_rows.json`). Funders not traced.

## Capital, timing, result

- Capital: flash-swapped inventory (no own principal visible in the traced fill).
- Timing: **timing wanted**.
- Window result (Olympus fills only, 7 d): 11 fills, gross measured on 1 (~0.26 USD), the rest unmeasured.

## What farm lacks / class

Nothing structural (atomic, flash-funded, one chain, ethereum private send available); what it lacks is a margin: the classes it works pay cents, shared with many rivals. **D** unless lead 183 measures fills that stay open >= 2 blocks with >= 0.5 USD gross.
