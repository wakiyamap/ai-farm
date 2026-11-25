---
type: infra
chains: [any]
protocols: []
author: meta/opus
updated: 2026-11-16
---
# Farm reaction time R per chain (race rule)

**In force (decision `2026-11-16-reaction-time`): ethereum R = 12 s (one block); every other chain R = 3 s.** The estimates in the table below for the other chains are not used until a real farm send is included on that chain; then the table is corrected with that send and meta tells the human. The counting rule (decision `2026-11-14-race-rule-seconds`) is unchanged.

Effect on ethereum classifications: none. With 12 s blocks, L = first block at or after T + 3 s and L = first block at or after T + 12 s are the same block (the next one), and "at least R after L" is block L+1 under both values (meta 6e5f9489, 2026-11-16; earners found no blocked_infra verdict that changes).

## The measured table (earner run 44446bcc, 2026-11-15, lead 192, 40 min probe 15:32-16:12Z)

R(chain) = feed detection p90 + send-to-inclusion median. Detection is live (farm-feed `/logs` long-poll and a relay poll at 10 s); send-to-inclusion exists for one ethereum send only; other chains use detection + one block time, marked (est).

| chain | feed detect med / p90 s (n) | 10 s poll detect med / p90 s (n) | send→inclusion s (n) | R = p90 + send s | measured? |
|---|---|---|---|---|---|
| ethereum | 2.02 / 3.50 (219) | 7.77 / 13.37 (250) | 8.06 (1) | **11.6** (send n=1) | det meas, send n=1 |
| base | 0.48 / 0.64 (7) | 4.31 / 6.00 (7) | 0.20 (0, est) | ~0.8 (est) | det meas thin, send est |
| arbitrum | 1.03 / 1.25 (5) | 4.79 / 11.32 (5) | 0.31 (0, est) | ~1.6 (est) | det meas thin, send est |
| bsc | 0.71 / 1.10 (7) | 3.69 / 7.26 (7) | 0.45 (0, est) | ~1.6 (est) | det meas thin, send est |
| polygon | -0.91 / -0.26 (750) | 5.96 / 8.62 (739) | 1.50 (0, est) | ~1.2 (est) | det meas, send est |
| avalanche | 0.00 / 0.00 (93) | 9.15 / 12.79 (90) | 0.92 (0, est) | ~0.9 (est) | det meas, send est |
| optimism | 0.14 / 0.17 (85) | 5.91 / 9.88 (89) | 2.00 (0, est) | ~2.2 (est) | det meas, send est |
| hyperevm | **no sample** (0 events in 49 min) | no sample | 0.98 (0, est) | ~2.0 (est: det ~1.0 feed delivery + 1 block) | estimate |
| elysium | 0.66 / 1.06 (900) | 6.61 / 10.35 (909) | 0.31 (0, est) | ~1.4 (est) | det meas, send est |

Avalanche's 0.00: arrival falls inside the same integer second as the (second-granularity, ~0.92 s cadence) block timestamp. Polygon's negative p90: PoS block timestamps run ~1 s ahead of the wall clock at delivery; the definition is kept as written.

A 10 s-polling bot's R = poll p90 + send: ethereum ~21 s; other chains est poll p90 + one block (polygon ~10 s, avalanche ~14 s, optimism ~12 s, elysium ~11 s, base ~6.2 s).

The dominant term is **send→inclusion (8.06 s on ethereum, n=1)**, not detection: feed detection is ≤ 3.5 s p90 on every sampled chain. Re-measure send→inclusion when more chains have live bots: the signer's response arrives before inclusion, so bots must log both the send wall time and the receipt's block timestamp.

## How each number was taken

- **Feed detection**: one modest event per chain through farm-feed `/logs`; latency = local arrival wall time − the log's `blockTimestamp`. Events: ethereum Aave v3 pool `0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2` topic0 `0x804c9b842b2748a22bb64b345453a3de7ca54a6ca45ce00d415894979e22897a` (~250/h); base `0x000000008a8330b5d1f43a62bf4c673a49f27ba0` / arbitrum `0xb274d5f4b833b61b340b654d600a864fb604a87c` / bsc `0x00000000a55e50c71b70db3c8b58749cd1e18eb2` UniswapX reactor `Fill(bytes32,address,address,uint256)`; polygon wPOL `0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270` Deposit; avalanche WAVAX `0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7` Deposit; optimism WETH `0x4200000000000000000000000000000000000006` Deposit; hyperevm Felix `Redemption(uint256,uint256,uint256,uint256,uint256)` on the 3 CDPs of the felix source; elysium USDC `0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65` Transfer (~1.7k/h; acceptable for an infra probe, a reviewer `fix` inside a bot).
- **Poll detection**: same events via relay `eth_getLogs` every 10 s; latency = poll return wall time − event block timestamp.
- **Send-to-inclusion**: the farm's only live send with both stamps: morpho-nextblock-ethereum `pool_init_sent` 2026-11-14T14:02:38.942Z, tx 0xdf25a9c7…, block 26413695 (ts 14:02:47) = 8.06 s, n = 1. It was the executor's pool-init setup tx, not a trading send, and the incumbent taker landed earlier in the same block (index 56 vs 169): landing in the next block does not mean landing ahead. Gate deploy/fund txs have no readable hand-time stamps.
- **One-block times** over 2000 blocks: base 0.20 s, elysium 0.31, arbitrum 0.31, bsc 0.45, avalanche 0.92, hyperevm 0.98, polygon 1.50, optimism 2.00, ethereum 12.0.
- Probe: `scratch/rt_probe/probe.py` (raw `feed_<chain>.jsonl`, `poll_<chain>.jsonl`), summary `scratch/rt_probe/stats.py`; research lane; ~12k feed CU.

## Caveats

- One 40-minute slice of one day; feed delivery varies with websocket lag (`infra/feed.md` ~1.0 s reproduced).
- Send→inclusion n=1 and mostly "wait for the next 12 s block"; nobody has measured it on sub-second chains.
