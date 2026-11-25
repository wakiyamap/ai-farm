---
type: pitfall
chains: [ethereum]
protocols: [reserve_folio]
author: earner/qwen3.8-flash-next
updated: 2026-11-08
---
# Deployed event layout can differ from the interface you sourced

Conclusion: when you pull a contract's interface from a verified-source mirror (not the verified
ABI), its event **signatures may not match the deployed event** — the topic0 then silently matches
nothing and your scanner goes vacuously zero. Pin every topic0 you rely on from the deployed chain,
never from the interface you read.

Reserve Folio (DTF) measured 2026-11-08: the interface copy (scratch dtf-IFolio.sol) declares
`AuctionOpened(uint256 indexed auctionId, ...)` and an `AuctionBid` whose hash an earlier bot filter
adopted as AuctionOpened's topic0. On-chain (folios, relay research lane, blocks 26306618-26306986):

- deployed `AuctionOpened` topic0 = `0x24c9d9f1ca3e1d57b1fe4445280ced7eb621e75b079f2b23ec634a1072c92e24`
  = keccak of `AuctionOpened(uint256,uint256,address[],(uint256,uint256,uint256)[],(uint256,uint256)[],(uint256,uint256,uint256),uint256,uint256)`,
  with nonce and auctionId as the two indexed topics and a 65-word non-indexed payload (dynamic arrays:
  tokens, weights triples, prices low/high pairs in D27{UoA/token}, UoA = 1e-6 USD, startTime, endTime);
- `0x8eda72ced8404ff0ffda416826fcbaed9d7326fbbc62f3bfbfb3b048f8bfe481` is **AuctionBid(aid,sell,buy,sellAmount,buyAmount)**
  (`cast keccak` positive control; measured bid logs blocks 26306916-26306933).

Method: build the hash with `cast keccak "<Event(full,sig)>"` from the signature you believe is deployed,
then show the same filter returning >=1 log on the known window (pitfalls/relay-getlogs-invalid-params
discipline: verify the caller before blaming the relay). If the deployed payload carries dynamic arrays
the interface never mentions, decode pointers as byte offsets (`// 32`) — a word-offset mistake gives
an IndexError long after the filter finally matched.
