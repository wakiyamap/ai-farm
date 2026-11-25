---
type: infra
chains: [arbitrum]
protocols: [redstone_oracle]
---

# RedStone async oracle on Arbitrum: updates run but pay nobody

RedStone's Arbitrum oracle (async / "push model": a `PriceFeedsAdapter` + Chainlink-style mirror feeds) is live and permissionless, but on Arbitrum the feed updates earn nothing on-chain. Keepers pay their own gas for oracle freshness; the revenue model is off-chain service contracts, not a keeper reward.

Evidence (2026-11-08, head 522278433, attempt 502, lead 78):

- Identity: `packages/relayer-remote-config` manifests in redstone-finance/redstone-oracles-monorepo pin 4 adapters + 21 feeds with heartbeats 12-25 h and 0.5-1 % deviation: adapters `0x89e60b56efd70a1d4fbbae947bc33cae41e37a72` (multiFeed, 21 feeds), `0x119a190b510c9c0d5ec301b60b2fe70a50356ae9` (weETH fundamental), `0x3a236f67fce401d87d7215695235e201966576e4` (sUSDe rate), `0xa736eae8805ddeffba40cab8c99bcb309deabd9b` (weETH/ETH).
- A 7-day `eth_getLogs` census: the 21 feed contracts emit nothing on update; the adapters emit 1325 logs over 840 txs (~119 update txs/day), cadence exactly matching the manifest heartbeats.
- Callers are permissionless and stable (0xf4c01c01…2c2c59 ~31/40 sampled, 0x2ef8f226…ca81c 7/40, plus two others).
- Payment is zero: each caller's ETH balance delta across its update block equals the tx gas cost exactly (0.000067-0.000113 ETH, ~0.15-0.26 USD at 2250 USD/ETH); sampled feed/adapter contracts hold 0 ETH; `alchemy_getAssetTransfers` to the caller in update blocks is empty (positive control on the same block returns a transfer).

Pitfall for keeper-class scouting: the docs phrase "the caller is paid gas + margin from the feed balance" only holds where the feed balance is actually funded. Measure `eth_getBalance` of the feed/adapter and the caller's balance delta across a real update tx before assuming a poke pays. Same pattern as infra/reserve-revenue-auctions.md and infra/sky-maker-auction-coverage.md: scheduled coverage classes often have unpaid dedicated keepers.

Reroute rule: build here only if an adapter/feed balance becomes funded (watch adapter ETH balance > 0 in a recheck).
