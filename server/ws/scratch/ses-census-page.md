---
type: mechanism
chains: [ethereum]
protocols: [morpho_blue]
author: earner/qwen3.8-flash-next
updated: 2026-11-11
---
# Morpho Blue ethereum pinned-market liquidation census (2026-11-11, decision 2026-11-12)

**Conclusion:** a 20 s poller on the farm's two pinned Morpho Blue ethereum markets is structurally too slow for this class. Over the 7 days ending 2026-11-11 the pinned-market captures were **1 liquidation liquidatable at the previous block's tail (C-1), 7 liquidated in the same block as the oracle update, 9 detected as underwater but correctly skipped below the 2 USDC + gas min-profit floor, and 1 missed by candidate eviction** — and the single C-1 capture's liquidation landed **one block** after the price update (Ethereum blocks are 12 s). The same-block ratio (8/17 including the one-block edge case) matches `methods/aave-v3-catchable-window-probe.md` (ethereum 75% oracle races); the difference is that Morpho's oracle is a Chainlink aggregator whose update lands in *one specific block* (Morpho `price()` reverts past `maxAge`), so the poller's only winning positions are the crossings that happened a full block earlier — 1 of 17 here.

## The probe (fork, per capture block C)

The eligibility test is the C-1 **tail**: `fork reset ethereum C-1` (the fork's `latest` is then the block *before* the capture — verify with `eth_getBlockByNumber` on both the fork and the relay), then replay the bot's own scan reads as plain `eth_call`s:

1. `idToMarketParams(bytes32)` (selector `0x2c3c9157` on Morpho `0xbbbbbb…ffcb`) → the market's `(loan, collateral, oracle, irm, lltv)`.
2. `accrueInterest((address,address,address,address,uint256))` (`0x151c1ade`) with that 5-word tuple — it accrues to the **fork's current block timestamp** (the C-1 block timestamp), exactly the interest state the next block's liquidator sees.
3. `market(bytes32)` (`0x5c60e39a`) → the *accrued* totals (words 3-4 = totalBorrow assets/shares).
4. `price()` (`0xa035b1fe`) on the market's oracle, `position(bytes32,address)` (`0x93c52062`) on the borrower.
5. `debtAssets = ceil(borrowShares·(tba+1)/(tbs+1e6))`, `collValue = collateral·price/1e36`, `maxDebt = collValue·lltv/1e18`; **liquidatable at C-1 iff `maxDebt < debtAssets`** (Morpho `_isHealthy`).
6. Repeat steps 2-4 at `C` (`fork reset C+1`, i.e. the capture-block tail) and compare `price`: a changed price = the oracle update landed in C-1..C; unchanged price + `hf(C-1) < 1` = a genuine poll window.

Calldata traps measured this session: the `bytes32` market id must keep its leading zeros (the RPC rejects a stripped `0x`, and `hashlib.sha256` is *not* keccak — take selectors from `cast sig`); `accrueInterest` reverts `market not created` if the tuple does not equal the stored config word-for-word; `eth_getLogs` params are `[filter, "latest"]`-style two-element arrays, not a flattened call.

## Evidence anchors

- C-1 liquidatable case (block 26384831, WBTC/USDC, repaid 92,326.04 USDC): probe `debtAssets` 92,325.998 USDC raw equals the `Liquidate` event `repaidAssets` to 5 wei, and `collateral` 1.4578 WBTC equals `seizedAssets/0.9` exactly — the probe reproduces the execution-time state; `hf(C-1) = 0.9987`, `price(C-1) == price(C)` (the update landed in C-1, liquidation one block later). The watcher's last scan read the **old** price (1.005094582819 health factor, 16 s before the capture); its next cycle was ~5 s after the liquidation.
- Race cases: the C-1-tail → C-tail price drops were −0.50%…−2.73%; the watcher's own cycle logs pin its first read of the new price to 7–23 s **after** each capture block (the liquidators saw the new round inside the block).
- `Liquidate` event decoding: `repaidAssets = principal·(1 + 0.03/lltv)` (incentive factor 1.0348837 at lltv 0.86 — the protocol caps the incentive at 1.15e18), `seizedAssets = principal_value·lltv/price`, so `debt_value = seized/lltv` and `collateral = seized/(lltv·price/1e36)` — the fastest way to sanity-check a probe against an event without tracing.

## Numbers (gross = repaid × 0.033692, the 3.37% incentive at lltv 0.86)

| class | captures | examples |
|---|---|---|
| C-1 liquidatable (poll window) | 1 | 92,326 USD repaid, gross 3,111 USD |
| same-block oracle update | 7 | 23,845 / 16,088 / 1,921 / 55,762 / 645 / 303 / 526 USD repaid |
| detected, below floor (skipped) | 9 | 30.6 / 22.8 / 3.9 / 0.91 / 0.007 / 0.0007 USD repaid — gross ≤ 1.03 USD vs a 2.065 USDC + 0.31 USD floor |
| never detected (candidate eviction) | 1 | 526 USD repaid, gross 17.7 USD |

## Metronome sES market-addition candidate: same race, same verdict (2026-11-11, run cce1b974)

The pinned-market census left "add markets after the classification" open, and the Metronome sES market (id `0xd263…1b0a`, 12 captures/7 d, two whale captures 26353674/26353682 repaying 51.19/23.10 sES) was the measured candidate — a paper bot (`morpho-ses-ethereum`) was placed on it the same day. The follow-on probe closed it the same way: sampled captures (both whales, the 26353519/26353520 and 26350419/26350420 pairs, 26342363) are **healthy at their C-1** under the probe's own step 5 rule — maxBorrow 656.31 vs borrowed 631.97 sES at the whale C-1 (margin 3.87 pct), margins 3.9–6.8 pct throughout — while the adapter `price()` is static `1.0998881240808278` across every tag 26353518…26353683 including the capture blocks. The crossings are intra-block (borrower or oracle action in the capture block itself), the identical pattern as the pinned markets. Trap: a liquidatability scan that only checks *repay feasibility* (can `seized ≤ debt` be repaid) without the `lltv` cushion calls these C-1 states liquidatable and reports windows ≥ 8192 blocks — the cushion matters at this margin (3.87 pct), and Morpho's `liquidate` reverts `HEALTHY_POSITION` (≈28.6k gas) on those C-1 states, which is exactly why the new bot's fork proof at reset 26353673 cannot produce a success tx. Per `decisions/human/2026-11-12-morpho-stop-researcher-runs.md` item 2 these captures are not counted in EV, so the sES route joins the closed class, not a new bot.

KB: attempts 943 (run cce1b974), leads 147 (`blocked_infra`). Repro: `scratch/morpho-ses-proof.js` + `scratch/ses-isliq-probe.py` (relay C-1 reads); the deployed Morpho exposes no external `isHealthy`/`isLiquidatable` (both empty-revert) — compute the step 5 math from `position`/`market` reads instead.

KB: attempts 926 (run 24d46866), lead 14. Repro scripts: `scratch/mwf-classify/c1-math.py` (C-1 math), `scratch/mwf-classify/c-price.py` (C tail).

## sES census completed: window 0 for all 12 events (2026-11-12, run 8a685418)

Decision 2026-11-12 item 3 asked for the time-to-take of all events. The six captures attempts:943 had not sampled were fork-probed with the `morpho-ses-ethereum` executor (`scratch/morpho-ses-proof.js`: reset `C-2`, `liquidate` lands at `C-1`): **all reverted `HEALTHY_POSITION`** (gasUsed ≈28.6k; C-1 cushions 3.9–6.8 pct — whale states at tags 26317643/26319397/26353680 read debt 684.08/627.56/580.83 sES against collateral 671.60/616.05/568.13 nETHMAX, HF 1.042–1.046). Together with the earlier sampling this closes all 12 in-window captures (blocks 26317645–26353682): each **became liquidatable inside its own capture block and was taken in the same block** — time-to-take 0 blocks / <12 s (avg block 12.03 s measured). The crossing is created by the block's own action: `liquidate` accrues interest to the call block (time since the market's last interaction at the IRM's high rate can add the ~4 pct needed), and/or the borrower re-borrows inside the capture block — the same borrower 0x14bcd9da is captured four times in the window, healthy at every C-1, incumbents land exactly at C. A polling bot has zero windows here; under item 2 the sES class has no counted EV and the new-ID paper bot was not placed.

Trap for census scripts: the deployed Morpho singleton exposes **no** external `isHealthy`/`isLiquidatable` (selectors `0x6eb71926`/`0x67c572ea` appear nowhere in the 15.6 kB deployed code; both calls empty-revert — `scratch/ses-isliq-probe.py` reverted for exactly this reason), and `accrueInterestExternal(bytes32,address,address,int256)` (`0xe5aa39bd`) is not deployed either — the only accrue route is the bot's 5-word `accrueInterest(tuple)` form.

KB: attempts 985 (run 8a685418), lead 147 (`blocked_infra`), actors 126/127 (incumbents 0xb3983cdd…, 0x3132d5ba…). Fork revert txs: 0xfd3fccecd1e3…, 0xa77397766835…, 0x82d4e8755139…, 0xec35beb71a33…, 0x3595948f9911…, 0x51e1aa5e4ab1….
