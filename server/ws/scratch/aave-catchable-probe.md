---
type: method
chains: [base, ethereum, arbitrum]
protocols: [aave_v3]
---

# Aave v3 catchable-window probe (interest-bleed vs oracle-update liquidations)

**Conclusion:** before building or reviewing an Aave v3 liquidation bot, measure what fraction of that chain's liquidations were *already underwater at the parent block* (`eth_call getUserAccountData(victim)` at `capture_block - 1`). Those are catchable by polling at any cadence; the rest are same-block oracle-update races no poller can win. Measured 2026-11-04 (run ebd18a98): **base 17/30 catchable (56.7%), ethereum 10/40 (25%), arbitrum unmeasurable retroactively** (relay paper-lane state depth ≤ ~8k blocks). On base, 16 of the 17 catchable windows were ≥ 342 s against an 8 s poll cadence.

## Why it matters

A poller (our bots) only competes on positions that sit below HF 1.0 for at least a few blocks. Events where HF was healthy at the parent block were triggered by a price/oracle tick **inside** the capture block — the winner saw the tick and acted atomically within one block (usually the same tx pattern or a MEV bundle). No polling cadence wins those; only event-triggered same-block racing does, which our infra does not do.

## The probe (pure node + relay, ~10-30 calls per event)

1. Get `(capture_block B, victim U)` pairs from `ledger` (`aave_v3.liquidation` events carry `user`).
2. `eth_call` `getUserAccountData(U)` (selector `0xbf92857c`) at `B-1` → word 5 (bytes 320-384 of the 6-word return) is `healthFactor`. Parent HF < 1e18 ⇒ catchable; else race.
3. For catchable events, binary-search the **first** underwater block: walk back with doubling steps until HF ≥ 1, then bisect. Window = `B - crossing_block`; multiply by the chain's block time (base 2 s, ethereum 12 s, arbitrum ~0.39 s... verify per chain).
4. At the capture block, HF = `2^256-1` means the liquidation repaid the entire debt (`debt == 0` afterwards ⇒ full liquidation).

Reference implementation: `scratch/aave-base-catchable/measure.js` (base) and `measure-eth.js` (ethereum), ~5 concurrent workers, retry ×3, call cap ~1600. Results: `out/catchable-class.json`, `out/catchable-class-ethereum.json`.

## Measured results (2026-11-04)

| chain | events | catchable (parent HF<1) | race_oracle | catchable windows |
|---|---|---|---|---|
| base | 30 | 17 (56.7%) | 13 (43.3%) | 24 s, 342 s, 2654 s, 2744 s, 13.2 ks, 13.7 ks, 30 ks, 44 ks, 123 ks, 128 ks, 203 ks, 204 ks, 5 × ≥ 5.8 d |
| ethereum | 40 | 10 (25%) | 30 (75%) | 12 s, 24 s, 600 s, 1224 s, 1368 s, then 4 × 20.8–25 h |
| arbitrum | — | blocked: state depth | — | measure live at next event (lead: aave-watcher-arbitrum catchable-window) |

- All 13 base races had parent HF within 0.45% of 1.0 (typical margin 0.04–0.40%) — oracle-tick snipes.
- Ethereum's races include a 14-position cascade liquidated in one block (26302299) — price-crash cascades are inherently same-block.
- Base's catchable class dominates ⇒ `aave-watcher-base`'s 8 s poll + HF<1.0 trigger is architecturally sound; ethereum is race-dominated ⇒ an ethereum Aave poller would catch only ~1/4 of events and would need a faster cadence for the rest.

## Pitfalls

- **Arbitrum retroactive probes don't work through the relay**: paper-lane historical state errors (`historical state ... is not available` / `missing trie node`) beyond ~7500–8000 blocks deep (~30–50 min at ~0.39 s/block). Base (≥ 250k blocks) and ethereum (≥ 10M blocks) serve deep state fine. Measure arbitrum live: at event time the parent block is fresh.
- `hf_at_capture == 2^256-1` is **debt fully repaid**, not an error (debt word is 0 ⇒ division saturates).
- Judge the window against the **bot's real decision latency** (poll cadence + sim time), not against zero: a 24 s window is catchable at 8 s polling but not at 2 min.
- Catchable ≠ profitable: long-window positions are often dust or exotic collateral; the bot's min-profit gate (`$1`) plus a same-tx revert-unless-profitable executor decide that separately.
