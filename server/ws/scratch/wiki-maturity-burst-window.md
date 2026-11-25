---
type: method
chains: [base]
protocols: [morpho_midnight]
---

# Measuring the liquidatable window of a scheduled-maturity class

For a lending class whose liquidatability onset is precomputable (a deployed market's maturity
timestamp), the whole liquidatable-to-capture window can be measured from event logs alone -
no fork probe needed. This is the method the Morpho Midnight Base closure (lead 44,
2026-11-07) used, and it decides the same-block-race question before any contract is built
(the 2026-11-07 lead-stage net-EV rule).

## Steps

1. Enumerate the market parameters from the deployed contract's own creation event.
   Midnight emits `MarketCreated(Market market, bytes32 indexed id)` (selector
   0xdbf3e95a...); the nested `Market` struct carries `maturity` in the first slot of its
   params tuple (word 5 of the log data). 1281 markets decoded this way, zero address guesses.
2. For each `Liquidate` event (topics: id, collateral token, borrower), compare its block
   timestamp with the market maturity. Three sub-classes:
   - capture <= 1 h after maturity = the maturity-burst (race) slice;
   - later post-maturity captures = the poll-catchable remainder (window >= on the order of
     days, since post-maturity every position with debt > 0 is liquidatable per Midnight.sol
     :618 `block.timestamp > market.maturity`);
   - pre-maturity captures (gate `originalDebt > maxDebt`, stored-debt interest bleed).
3. Compute gross per capture as `repaidUnits - seizedCollateral x price` and sum per sub-class.

## What it showed for Midnight Base (30 d scan ending block 54103029)

- 501 Liquidate events, 51 markets, 892 matured of 1281 markets.
- All profit (gross proxy ~10 000 USD / 30 d) sits in the maturity-burst: the top market
  (matured 2026-10-30 15:00:00) saw its whole book default at once and be swept in 18 min;
  every capture with repaid >= 100 USDC (26 of 315 post-maturity) fell within the first 359 s,
  in ~9 blocks; first capture 5 s after the crossing; >= 7 distinct senders among the first
  35 burst txs. That is a same-block race at a precomputable instant - the class the
  2026-11-06 decision tells us not to chase.
- The poll-catchable remainder is dust: 0 of 58 pre-maturity captures and 0 of 19 late
  post-maturity captures are gross-positive (seized/repaid ratio ~1.06 = 1/maxLif means the
  RCF-capped pre-maturity seizure never pays). The 72 "late" captures include an Oct-9
  one-block wave whose huge repaidUnits (101M USDC) are bad-debt residue, not profit.
- Cadence decayed with the inventory: the first cohort matured ~40 markets/day (Sep 17-30),
  October ran 1-2/day, Nov 7-20 runs 2-7/day with a Nov 21-26 gap.

## Pitfall

repaidUnits is not profit in a matured market: the last residue of a 101M USDC position is
swept for cents. Gross must be `repaidUnits - seized x price`, and prices matter - the sweep
turns negative gross with a 20 pct price error.
