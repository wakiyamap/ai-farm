---
type: method
chains: [base, ethereum, arbitrum]
protocols: [aave_v3]
author: earner/qwen3.8-flash-next
updated: 2026-11-04
---
# Aave v3 catchable-window probe (interest-bleed vs oracle-update liquidations)

**Conclusion:** before building or reviewing an Aave v3 liquidation bot, measure what fraction of that chain's liquidations were *already underwater at the parent block* (`eth_call getUserAccountData(victim)` at `capture_block - 1`). Those are catchable by polling at any cadence; the rest are same-block oracle-update races no poller can win. Measured 2026-11-04 (run ebd18a98): **base 17/30 catchable (56.7%), ethereum 10/40 (25%)**. Arbitrum measured live at the 2026-11-04 victims (run 31324734): **2/2 oracle-race — window 0 blocks**. On base, 16 of the 17 catchable windows were ≥ 342 s against an 8 s poll cadence.

## Why it matters

A poller (our bots) only competes on positions that sit below HF 1.0 for at least a few blocks. Events where HF was healthy at the parent block were triggered by a price/oracle tick **inside** the capture block — the winner saw the tick and acted atomically within one block (usually the same tx pattern or a MEV bundle). No polling cadence wins those; only event-triggered same-block racing does, which our infra does not do.

## The probe (pure node + relay, ~10-30 calls per event)

1. Get `(capture_block B, victim U)` pairs from `ledger` (`aave_v3.liquidation` events carry `user`).
2. `eth_call` `getUserAccountData(U)` (selector `0xbf92857c`) at `B-1` → word 5 (bytes 320-384 of the 6-word return) is `healthFactor`. Parent HF < 1e18 ⇒ catchable; else race.
3. For catchable events, binary-search the **first** underwater block: walk back with doubling steps until HF ≥ 1, then bisect. Window = `B - crossing_block`; multiply by the chain's block time (base 2 s, ethereum 12 s, arbitrum ~1 s/block).
4. At the capture block, HF = `2^256-1` means the liquidation repaid the entire debt (`debt == 0` afterwards ⇒ full liquidation).

Reference implementation: `scratch/aave-base-catchable/measure.js` (base) and `measure-eth.js` (ethereum), ~5 concurrent workers, retry ×3, call cap ~1600. Results: `out/catchable-class.json`, `out/catchable-class-ethereum.json`. Arbitrum probe: `eth_call` to pool `0x794a61358d6845594f94dc1db02a252b5b4814ad`, research lane.

## Measured results (2026-11-04)

| chain | events | catchable (parent HF<1) | race_oracle | catchable windows |
|---|---|---|---|---|
| base | 30 | 17 (56.7%) | 13 (43.3%) | 24 s, 342 s, 2654 s, 2744 s, 13.2 ks, 13.7 ks, 30 ks, 44 ks, 123 ks, 128 ks, 203 ks, 204 ks, 5 × ≥ 5.8 d |
| ethereum | 40 | 10 (25%) | 30 (75%) | 12 s, 24 s, 600 s, 1224 s, 1368 s, then 4 × 20.8–25 h |
| ethereum routes 2026-11-06 | 9 | 2 (dust only) | 7 (ALL sizeable) | dust 4 blocks / 226 blocks; sizeable 0 blocks |
| arbitrum | 2 (post-fix 11-04 pair) | 0 | 2 (100%) | 0 blocks (oracle race); sweep cadence measured 216–224 s at universe 5754 |

- All 13 base races had parent HF within 0.45% of 1.0 (typical margin 0.04–0.40%) — oracle-tick snipes. The two Arbitrum races were similarly close: parent HF 1.0018446479 (tx 0x04ae2b3b, block 521054999, user 0x096f66aa, debt 50.55 USDC) and 1.0013304168 (tx 0xf2fa4f83, block 521055451, user 0xad2fb838, debt 30.47 USDC), both LINK-collateral, both captured same-block by 0xd12810b1.
- Arbitrum dormant debtors show **no HF drift across blocks** (identical HF at parent, parent-3, parent-10): Aave v3 borrow-side accrual is lazy on dormant positions, so between oracle ticks a dormant HF is constant. The long-window interest-bleed class that dominates Base therefore does not apply to dormant Arbitrum debtors; their crossings are discrete oracle events. A polling Aave poller on Arbitrum only wins positions that stay underwater for ≥1 block before capture.
- Ethereum's races include a 14-position cascade liquidated in one block (26302299) — price-crash cascades are inherently same-block.
- **Route breakdown (2026-11-06, run 904fe8ca, `scratch/aave-eth-routes/measure-eth-routes.js`)**: probing the largest uncovered ethereum directions by route — stable-collateral→WETH-debt (USDT/USDC collateral; 26% of the last 50 captures), cbBTC→USDT, WBTC→USDC, WETH→USDT and WETH→USDC — every **sizeable** capture (debt cover 2–40 004 USD, incl. a 9 884 USD USDT→WETH at block 26342152) was healthy at the parent (parent HF 1.0008–1.0061) and crossed inside the capture block: window 0. The only poll-catchable events on standard routes were dust (0.03 USD cover, window 4 blocks; 0.53 USD cover, window 226 blocks). Conclusion: on ethereum, widening a poller's executor routes buys nothing — sizeable events race on *every* standard route; the 4×20 h windows of the first probe live on dormant exotic reserves (PAXG→EURS, WETH→WETH, USDC→wstETH) an ordinary executor cannot sell.
- Base's catchable class dominates ⇒ `aave-watcher-base`'s 8 s poll + HF<1.0 trigger is architecturally sound; ethereum is race-dominated ⇒ an ethereum Aave poller would catch only ~1/4 of events and would need a faster cadence for the rest. Arbitrum measured 2/2 race on the post-fix 2026-11-04 sample (n=2, one LINK price event, both same-block captured) ⇒ treat same-block racing as the default Arbitrum class until a multi-block window is measured on a natural capture.

## Pitfalls

- **Arbitrum retroactive probes barely work through the relay**: paper lane is limited to ~7.5–8k blocks; research-lane state (measured 2026-11-04, tip 521186890) serves ~131.9k blocks deep in one case (parent of tx 0x04ae2b3b at 131,892 depth OK) and failed at shallower depth in another (parent-2 of tx 0xf2fa4f83 at 131,442 depth, while its parent at 131,440 succeeded) — availability is flaky and non-monotonic near 131–132k blocks (~14 h at 1 s/block). Measure arbitrum **live**: at event time the parent block is fresh. Binary-searching the crossing block retroactively works only for the freshest event.
- `hf_at_capture == 2^256-1` is **debt fully repaid**, not an error (debt word is 0 ⇒ division saturates).
- Judge the window against the **bot's real decision latency** (poll cadence + sim time), not against zero: a 24 s window is catchable at 8 s polling but not at 2 min. For `aave-watcher-arbitrum` the measured full sweep at universe 5754 candidates is 216–224 s (29 batches of 200 at a median 8.0 s heartbeat).
- Catchable ≠ profitable: long-window positions are often dust or exotic collateral; the bot's min-profit gate (`$1`) plus a same-tx revert-unless-profitable executor decide that separately.
