---
type: pitfall
chains: [ethereum]
protocols: [pendle_v2]
---

# Event topic0 changes with every event-arg version: censuses on newer factory deployments go vacuously zero

A topic scan over a contract that deployed several factory versions (or an event whose ABI gained a trailing argument) matches only the version whose signature you hashed. The scan returns `[]` on every newer deployment and looks like dormancy.

Measured 2026-11-07 (run f7998b9e, relay research lane head 26365236): Pendle's DefiLlama adapter hardcodes the 4-arg `CreateNewMarket(address,address,int256,int256)` topic0 0x166ae5f5... for all five ethereum factories; that topic matches only the v1 factory (4 logs in its own launch window 16032060-16132060). The v3-v6 factories emit the 5-arg variant `CreateNewMarket(address,address,int256,int256,uint256)` = topic0 0xae811fae25e2770b6bd1dcb1475657e8c3a976f91d1ebf081271db08eef920af: the latest v6 factory shows 44 creations in the last 100 days, last at block 26354724, while the same scan with the 4-arg topic returned 0 across every newer factory's whole lifetime (attempts 447, 448 - one session, recorded then reversed).

Rule: when a zero comes from a topic0 copied from an adapter or an old receipt, first run the same filter over a window where the OLDEST deployment must have events (positive control) and check the event ABI for a trailing-argument variant (`cast keccak "Event(<old args>)"` vs `cast keccak "Event(<old args>,uint256)"`). A `[]` with no version check is your selector, not the chain.
