---
type: infra
chains: [ethereum]
protocols: [yearn_v3]
---
# Yearn-periphery-style Dutch `Auction` contracts (AuctionKicked): alive, professionally contested (2026-11-11)

**Conclusion.** Contracts with the Yearn tokenized-strategy-periphery `Auction` ABI sell strategy reward/fee tokens for a `want()` token through a Dutch price, and anyone may `take` with a callback. On Ethereum the class is busy: **369 `AuctionKicked(address,uint256)` events in 30 days over 42 auction contracts, and 330 take-topic txs**. It is already taken by at least 8 specialist searchers at thin margins. **Not worth a farm bot. Not installed in the ledger.** Measured as a quick census only (run 1a4364c4, about 15 min). Lot values per day were not summed.

## Evidence
- topic0 `AuctionKicked(address,uint256)` = `0xb3831db58b36bd77258a9cc9589b88fab5d52f7a1814e6f17faec14b149fe084`. Topic-only `eth_getLogs` on ethereum blocks 26174138-26390138 returned 369 logs. The top emitters are `0xa00e6b35c23442fa9d5149cba5dd94623ffe6693` (72), `0xba21b0844ab5acdced351203d8a8c5fc942c0f75` (58) and `0x73b2962d10e5dda7768c55dbe8f24a78149ced0c` (30). The emitters are minimal proxies (46-byte code); `0xa00e6b35` delegates to `0xecdfb5bebb9e72ca7c8b6aeeb0ca07375c1c0b2e`, with `want()` = crvUSD and `receiver()` = `0xb911fcce8d5afcec73e072653107260bb23c1ee8`.
- The take-side event on these emitters is topic0 `0x3539af76bcb13fa381f2ec32e6d90b9c5e95055778ebdca0e7a192ba07755881` (330 logs / 330 txs over the 42 emitters, same window; the signature was not resolved).
- Take tx `0x6e2e1a00515a7be18c1f3374a59d11ff504bd10c5c24252f1bc670b5208ce68c`: searcher `0xfb076e0b...` called `0x000000ae384600d7252543855e3b0400f6008d00`, which took 1920.04 USDC, routed it through KyberSwap (`0x6131b5fa...`), paid 1923.50 crvUSD and kept **0.241 crvUSD** (about 0.0125%) at 470k gas.
- Taker census (200 of 330 take txs, by tx.from): `0xa88e98bbd2af6ddd642407cb5455f956f0c553f0` 103 (self-call, likely EIP-7702), `0xfb076e0b813cc205a2d032b639f6d10f500dd9b7` 49, `0x84483314d2ad44aa96839f048193ce9750aa66b0` 15, `0x814532014ff844e6c976367eb23bc61c78e820f0` 12, c0ffeebabe `0xc0ffeebabe5d496b2dde509f9fa189c25cf29671` 7, and 3 more.

## Why not
Margins are about 0.01% of the lot, and an incumbent with 52% share plus at least 7 other searchers already crosses each auction at break-even with aggregator routing. That is a latency/routing race (decisions/human/2026-11-06-no-latency-race.md). Reopen only on a chain where the same ABI has kicks but no takers: run the same topic scan there, since per-chain coverage beyond ethereum was not measured.
