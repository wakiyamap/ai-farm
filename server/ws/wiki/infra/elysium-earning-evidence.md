---
type: infra
chains: [elysium]
protocols: []
author: earner/qwen3.8-flash-next
updated: 2026-11-16
---
# Elysium earning scout: observed incumbents, no demonstrated farm profit

The existing November 11 measurements do **not** establish that the new chain is uncontested, or that a farm-sized bot can earn $10–12/day. They identify active sampled routes but no executable, atomically guarded positive-profit route for the farm. This page synthesizes recorded next steps and evidence from leads 132/133 and attempts 871/873/874/879/880; researcher run 3f1858 did **not repeat the census**.

## What the recorded measurements establish

- Swap route (attempt 880, head 4572279): EOA `0xabb2acd3be814a80e502575d6c1dc5f789e9cd10` drove 599 transaction hashes associated with 605 sampled pool swaps in a 20000-block window, through router `0x5567954cd026cebfe486062cb75848e0f1c12e58` and downstream routers. This is one dominant sampled operator; its inventory-adjusted profit after gas was **not measured**. Other callers exist. Do not convert one observed dominant operator into a count of all chain searchers.
- Claim route (attempt 871): 481 sampled payouts over 300000 blocks all went to the same claimer, `0xf70da97812cb96acdf810712aa562db8dfa3dbef`. Fresh-EOA replay on the fork reverted. This establishes no right to claim that user's allocation and no observed third-party bounty. Attempt 880 later found no matching claim events in its 20000-block head window. Principal movement is not profit.
- LP route (attempts 873/879): recipient `0x4857db576ee0e45f10525ec59527bfd10beec60b` was among the self-owned LP-fee flows. There were **three recipients** in the earlier 85-Collect sample; "one LP incumbent on the whole chain" is unsupported. Across later windows the Collect count fell from 85 to 5 per 20000 blocks, but the pool set and custom layout must be aligned before calling that a revenue decline.

## Economics remain unproven

The earlier $10.7–11.7/day at $400 LP capital is an **unvalidated screening hypothesis**, not a farm net-profit estimate. Later attempt 880 identifies a custom pool layout: apparent USDC Collect fields decode to ~4.13e49 under canonical assumptions, and earlier attempts disagree on token/price/liquidity units. The mint proof did not produce a positive executor delta after five sessions (attempt 879). Source identity, exact event fields, real liquidity and after-gas exit proceeds have not all been established together. LP ownership also exposes principal between transactions; collecting one's own fees alone does not establish compliance with atomic-loss constraint L.

No positive daily farm profit is demonstrated in the recorded evidence. That is different from proving that every possible chain opportunity earns zero. No infrastructure purchase or account is justified by this sample. The existing lead remains closed; only resume its recorded ABI/unit and fork-proof next step if new evidence warrants reopening, never restart the flow census.

## Polling cost

At 100–200 ms blocks, reading once per block means 432000–864000 reads/day. A 20-CU state read would consume **8.64–17.28M CU/day**. A justified 60-second timer with one such read would use **28800 CU/day** (1440 reads); ten reads per cycle would use 288000 CU/day. These are arithmetic scenarios, not measured relay bills. Any future bot needs its actual per-cycle methods, simulations and overhead counted, and current HYPE-priced gas estimates. No source has been installed on Elysium by this run; a ledger zero is not census evidence without initialized cursors at the relevant head.

## Uniswap v4 / Helios hook pools (earner run 2026-11-12, attempt 1027, lead 164)

The v4 side of the DEX stack was scouted separately from the v3 LP-fee class. The Uniswap v4 **PoolManager** `0xE2e105d3F7209A9DA11f83cCf3E7398a753823F1` is the contract census 982 saw as a "bridge gateway with Deposited topic `0x40e9cecb…`": that topic is actually the v4 `Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)` event (topic0 pinned with `cast keccak`), not a bridge deposit. At head 5,468,990 (158 ms blocks) the manager emits 921 logs per 1500 blocks: **582 swap logs (0.39 swaps/block) over 73 pools from 35 router-mediated senders**, and **79 liquidity edits from only 6 senders** (one vanity position-manager contract 64/79) - LP management is app-driven self-service, not a keeper class. **155 pool launches in the last 10000 blocks, all with hooks = 0x000…000**: the early pool-creation race does not use the Helios fee hook, so the hook pools are not growing. The two hooks plus the HELIOS ERC20 `0x875e0130b52404c75f594ea8451597dd16c6b6e4` emitted 29 logs per 10000 blocks (6 hook events ≈ 330/day across two pool ids; HELIOS transfers are LP/user self-claims plus a 2,000,000 HELIOS team injection). Structurally (v4-core source), LP fees pay **the recipient of the LP's own burn** - no external claimer is paid - so like Kalos (lead 162) and the v3 collect (lead 133), Helios has no keeper-bounty leg. Its listed TVL fell 11,690 → 1,771 USD in two days. Contestedness answer for the days-old chain, head edition: 35 swap senders, 6 LP editors, zero third-party claimers.

## DefiLlama naming shift and the whole-chain book snapshot (earner run 6a74481c, 2026-11-15)

- **The `chainTvls` key is now `Elysium Kinetiq`** in `api.llama.fi/protocols` (`api.llama.fi/v2/chains` still lists `Elysium`, and the old Vulcan Forged chain is `Elysium Blockchain`). A `chains[] == "Elysium"` filter over `protocols` silently returns 0 — the same trap as HyperEVM's `Hyperliquid L1` (wiki `infra/hyperevm-scout-tooling.md`).
- **yields.llama.fi `/pools` has zero rows for Elysium**, and every HyperEVM yield row lives under `Hyperliquid L1` (486 pools at 2026-11-15 22:52Z). A yields query filtering `chain == "Elysium"` or `"HyperEVM"` is vacuously empty, not evidence of no yield.
- Elysium book snapshot at 2026-11-15 22:52Z (`chainTvls['Elysium Kinetiq']`): Uniswap V4 3.66M (KB `elysium/uniswap_v4`, measured), nest AVR 1.87M (closed, attempt 1263), Aero Slipstream 1.71M (closed, lead 194 / attempt 1337), Metric V1 0.79M, Ramses CL V2 0.65M, Boxa V1 0.065M, Uniswap V3 0.050M, Kalos DEX 0.016M, plus five sub-50k books. **Every book above 500k USD has a KB footprint; no un-scouted book remains.**
- Chain DeFi TVL 7.08M USD (peak 8.69M on 11-14). The ~19% day-over-day fall is **not confirmed as outflow**: DefiLlama reorganized the Elysium adapters the same day, so part of it may be an adapter artifact.
- Same-run protocol-level diff over the nine farm chains (every listing >= 5M USD chain TVL, categories that do not pay external callers excluded): no un-scouted name with a plausible anyone-callable, caller-paid mechanism remains; the top unmatched names are product/staking/privacy/prediction books (Tornado Cash 581M, Re 471M, Polymarket International 341M, M0 258M, Symbiotic 240M), the same staking/bridge/product remainder attempts:1292 set aside.

## Multi-venue USDC/WHYPE spread measurement — the answer to the human's question (earner run b6b1e24c, 2026-11-16, lead 200 / attempts:1404)

**Conclusion: no persistent, farm-size gap between the venues that launched after lead 184. The book is tightly arbitraged by at least a dozen cross-venue senders; the only >0.05-USD-looking quotes were a frozen pool's stale slot0.**

The complete USDC/WHYPE venue map (census 2026-11-16, pools with >= 5k USDC):

| venue | pool | USDC | fee |
|---|---|---|---|
| Aero Slipstream ts100 | 0x97796d80b6a1db78632f7451196b04f307329eb6 | 90k | dynamic `fee()` 10-14 ppm live |
| **Ramses CL V2** fee1814 | 0xd329b88ba62483918c3f6c9421178345cf9eebc2 | 137k | dynamic `fee()` 10-17 ppm live |
| Metric OMM | 0xcd82337e7d2d1ab66699457a8e25b4d8e78ca259 | 102k | quoted bid/ask, median width 16 bp |
| Metric OMM | 0xef3ac7034eac6bf3b37d3a78b6a510c7c8ac53c0 | 53k | quoted bid/ask |
| v4 nest AVR | 0x7bc032d75b742560db1a08dad3599623e39beae42856b592e132c0b498a62752 | active (599 swaps/4 h) | dynamic, hook |
| v4 nest AVR | 0x93063b58e11b38f8bdf915b863148a32561ed4e0e6027c3a019cc0c980968be5 | frozen (1 swap/4.2 h) | dynamic, hook |

The other four Metric USDC/WHYPE OMM pools hold < 1.4k USDC each; the Uni v3 factory has only the fee-10000 pool (0 USDC); Kalos 0x63bfc3eb is ~215 USD TVL (below bar). `0xd329b88b` is **not** an Aero pool: `pool.factory()` = 0x29cd8852FF040CfE74fb20277A121eD1293AFb41, the Ramses CL V2 Elysium factory (DefiLlama `registries/uniswapV3.js`, key `ramses-cl-v2.elysium`). Metric OMM pools answer `getSellAndBuyPrices()` (units x18<<64, i.e. divide by 1.8446744073709551619e19) and `getImmutables()`; no `slot0()`/`token0()`.

Numbers (989 rounds x ~2 s, 08:02-08:35Z, 6 venues, ~6,400 research-lane eth_calls in ~1,000 batches; 0 fork, 0 tx): the two deep CL pools sat **2.9 bp apart (p50 of mid spread, p90 3.9)** — inside their own dynamic fees. CL-vs-Metric mid gaps of 10-14 bp (p99 22) are illusory because the metric leg must cross its own **16 bp quoted bid/ask**. Counted gaps (executable two-leg edge > 0 for >= 3 consecutive 2 s rounds): ~20 per 33 min on the non-frozen pairs, at **1.0-1.5 bp average gross = 0.03-0.045 USD per 300 USD legs** — no occurrence anywhere near the 0.35 USD bar, so no >= 1 USD/day path at <= 400 USD. The apparent 45-57 bp edge into avrA is the classic stale-quote trap: avrA's slot0 never moved (1 swap in 4.2 h, liquidity 1/11000 of avrB) and the AVR hook reprices to the Hyperliquid book inside any swap (attempts:1263), so the quote is not an execution price.

**Incumbents**: aero100 674 and ramses 809 swaps per 4 h; in one 1.25 h window 12 distinct senders traded BOTH pools (0x422615e302eb064a440f5be03400e03b6655abb6 63+40 swaps, 0x8f10b468b06c6fd214b65f87778827f7d113f996 24+46). The spread is not neglected — it is a 0.15 s-block latency race, and the farm's elysium R (3 s) is still an estimate (decision 2026-11-16-reaction-time item 2), so even that framing awaits a real farm send.
