---
type: pitfall
chains: [base, ethereum]
protocols: [morpho_blue]
---
# Morpho oracle price scales are per-market — do not transplant the base 1e36 divisor

Conclusion first: the healthy-check formula `borrowed > floor(floor(coll*price/1e36) * lltv / 1e18)`
that `morpho-watcher-base` measured to the wei on **base** does NOT transfer to the same Morpho
singleton on **ethereum**: with the same code and the same vanity address
`0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb`, the ethereum market oracles return prices ~1e3
(WETH/USDC) and ~1e1 (WBTC/USDC) higher than the divisor the base formula expects, so the
divisor must be **calibrated per market** before the poller trusts its health math. A bot that
copies `coll*price/1e36` verbatim onto ethereum marks every position healthy and never fires.

Evidence (measured 2026-11-04, run 50b1fd0b): on the WETH/USDC market `0x94b823e6…` the oracle
`0x0f948cba8231db7898ef36a4212581ad7b1b4580` returned `price() = 2.26691546842e30` (ETH at
2266.91546842 USD) at block 26328589; Liquidate event calibrations: seizes `3.94380632960179e16`
WETH-wei with `repaid = 85163563` USDC-wei (tx `0x0969c9fde98d4c9ef51b82c7f3b5dde23fd11170befb55c052328f59edc7b94f`,
block 26328590) give `seized*price/repaid = 1.0495e39`, i.e. divisor `1e39`, penalty 1.0495 —
verified on three events (blocks 26295008, 26322217, 26328590). On the WBTC/USDC market
`0x3a85e619…` the oracle `0xdddd770badd886df3864029e4b377b5f6a2b6b83` returned
`7.6562e39` at block 26338615, and the capture at block 26338616 (tx `0xc790bdc9b0814a4e759c4e04afacd0ca8ebcdddb62b8e1ecbfce6d65ab30c352`,
seize `1310336` WBTC-wei, repaid `956072482`) calibrates divisor `1e37`, same penalty 1.0495.

Method that always works: calibrate the divisor `D` per market from one real Liquidate event,
`D = seized_assets * oracle_price / repaid_assets` rounded to a power of 10, and sanity-check
that the implied penalty `seized*price/D/repaid` lands in `[1.00, 1.12]` (Morpho's liquidation
penalty range). Same-chain copies of the base bot (`scratch/morpho-eth-hf.js` is a working
reference) should then reuse the base eligibility formula with `price/1e36` replaced by
`price/D`.
