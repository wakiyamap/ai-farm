---
type: mechanism
chains: [ethereum]
protocols: [reserve_folio_dtf]
---

# Reserve DTF rebalance auctions (Folio Dutch pair decay)

Conclusion: a permissionless bot can take a measured 6-480 pct discount on Reserve Folio (DTF)
rebalance auctions, the bid timing is precomputable from the auction's own parameters (no
same-block race), and the payment leg (deficit tokens) is the open design question.

## The mechanism (pinned from reserve-protocol/reserve-index-dtf main, fetched 2026-11-08)

- A REBALANCE_MANAGER starts a rebalance (`startRebalance`, role-gated); the AUCTION_LAUNCHER
  (or anyone, after the restricted window: `openAuctionUnrestricted`) opens Dutch auctions on
  token pairs. Only pairs with the sell token in surplus and the buy token in deficit are
  eligible, so a rebalance is always "sell overweight for underweight".
- `bid(auctionId, sellToken, buyToken, sellAmount, maxBuyAmount)` is permissionless and has no
  caller reward: the whole payment is the price corridor. The bidder receives sell tokens and
  pays buy tokens.
- Each token carries a price corridor `[pessimistic, optimistic]` in USD x 1e18 per token unit
  (the manager's oracle reading at rebalance start, e.g. the leader folio's Marvell low
  67.4575). The price of a pair interpolates along an exponential decay curve
  (RebalancingLib.sol:472-493): `startPrice = sell.high x D27 / buy.low`, `endPrice = sell.low
  x D27 / buy.high`, `price(t) = startPrice x exp(-k t)`, `k = ln(startPrice / endPrice) /
  auctionLength`.

## Measured (30 d census, blocks 26140177-26370177; attempts 546, 549)

- 28 Folios deployed, 5 with open rebalances, 73 bids / 25 d (2.4/day) shared among four
  incumbents (0x492a0579..., 0xc0ffeebabe..., 0x00aa588b..., 0x95bccaf5...) plus one-shots.
- Leader-folio pairs have corridor 256 over the 1800 s auction: `k = ln(256)/1800` = 3.7 pct per
  block. A 16-bid race over 17 consecutive blocks (26306916-26306933) shows bids paying
  0.1106 -> 0.0612 Marvell per 0.3 Broadcom exactly on the curve.
- The two largest fills reproduce the on-chain price: 57.58 Constellation for 9.0576 Marvell at
  83 pct of auction 8 (tx 0x773a7b4c03f31d849210ff3f7c5b19a2c79c0b7c4736b20df57cddc74fa871e6),
  2.19 Micron for 7.2661 Marvell at 53 pct (tx 0x23b2213a13a780a8d058955aefd26577eb8f043beb374da1d2be3998bc0a3478).
- Taking the corridor low as the market price at rebalance start, the value multiple received
  over paid is 1.06x for a mid-auction bid and 5.79x for the 83 pct bid: a bidder who waits
  earns the decay. All 13 RebalanceStarted events sit in the last 2 days of the window -
  the Folios are newly activated and no long-term cadence history exists yet.

## Pitfalls

- Prices are per-token-unit in the manager's BU scale (typically 1e18); the dust folio uses a
  different scale (its WETH row 2000-3000 is ETH/USD at 1e27 scale) - never copy a price scale
  from one folio to another.
- The corridor low is an oracle reading at rebalance start, not a live spot price; a fill can
  legitimately sit below any external quote you compare it to.
- The reserve_folio.auction_bid ledger source (installed by run 911a4eaa) started ingesting on
  2026-11-08 with its cursor at the install head 26355911 - the census fills before the install
  live only in scratch/dtf-census-30d.json. A single early `ledger sources` read showed nothing;
  re-check before concluding a source is missing.
