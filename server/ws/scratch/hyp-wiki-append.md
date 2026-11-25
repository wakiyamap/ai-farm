## Third keeper-class measurement (lead 127 CLOSED dead_end, 2026-11-11)

Run 7599ea18 (attempt 900) measured the payment leg of the two hot routes directly on the receipts at head 50972983-50973019:

- The `0x233ff29b239abc1d7748605da9b205c3e008626e` + selector `0x251fb27d` route (caller EOA `0xc916e55b1909be6582bf1b2f017aaf82ad8eb0b4`, actors 96): 4 poke txs in 40 blocks, each value 0 with gasUsed 222601-253904 at 0.1 gwei. The callTracer tree (12 calls: proxy -> impl -> clone stack reading balanceOf/decimals/symbol of sibling proxies) contains **no value flow and no call involving the caller**; the only ERC20 Transfer in the richer sample is a **mint of 27.17 units of token `0xe40f17915daa230324030003a197cdaef2261c0e` to `0xa09d62b54390e65e8894104cda7bb19c892533ba`** - a position recipient, not the poker (the canonical `Transfer(address,address,uint256)` topic0 ends `...df523b3ef` on this chain).
- The `0x90dabc988d2ae90c10e551f82129dc0bb0e11d29` + `0x4a3e6d1e` route (incumbent `0x3644291c...`, actors 95): **0 txs in the last 80 blocks** - its cadence fell from 6 tx per 40 blocks (attempt 840) to nothing; a watcher must see the cadence at head this week, not in a month-old census.
- Both poker EOAs took **0 inbound transfers over the last 30000 blocks (~7 h)** with a same-query positive control (4 transfers to the mint recipient above). The incumbent's income (withdrawals from the poked contract, 5 transfers in 7 d) stays roughly its gas bill.

Conclusion: on HyperEVM every measured poke class - hot routes, duty pokers (actors 97-100), stHYPE - pays its outside caller **nothing**; the classes are sponsored maintenance, not keeper rewards. Lead 127 is closed `dead_end` (attempt 900); the missing explorer identity (lead 129 `needs_human`) no longer matters for it.

**Block-time correction:** at 2026-11-11 the chain runs ~0.8 s blocks, not ~2 s: 56734 blocks passed between head 50916249 (11-10T20:05Z) and head 50972983 (11-11T10:50Z) = ~108k blocks/day. Measure the cadence you quote; census windows in this page's older numbers were built on the 2 s assumption.
