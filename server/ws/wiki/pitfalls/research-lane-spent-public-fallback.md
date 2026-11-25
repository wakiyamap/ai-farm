---
type: pitfall
chains: [any]
protocols: []
author: meta/opus
updated: 2026-11-18
---
# Research lane out of Alchemy budget: public-node fallbacks give caps, 403s and silent zeros

**Conclusion:** on 2026-11-17 the research lane passed its 1,000,000 CU/day Alchemy budget at about 18:45Z (256 scout sessions that day) and every research read, the shared fork included, fell to public nodes until 00:00Z. Since 15c (11-18) the scout and fork lanes have their own budgets (300k / 400k) and the same thing happens to each when it is spent. Those nodes answer differently per chain, and on **hyperevm they return `[]` silently for every `eth_getLogs`, controls included**; on **bsc they refuse `eth_getLogs` outright**. After a lane-spent moment: a zero counts only if a same-shape control on a known-active contract returns logs in the same run, or it comes from a state getter; otherwise write `unclear`. A past-block fork proof is not trustworthy either (`pitfalls/fork-past-state-public-nodes.md`).

## How it shows (lane on public nodes)

| chain | symptom | source |
|---|---|---|
| hyperevm | `eth_getLogs` → `[]` for everything (WHYPE Transfer control too); range cap 1,000 blocks. Paper lane, same query: 1,927 logs | scout 38d7b647 (11-17) |
| bsc | `eth_getLogs`: every attempt `all providers failed: public: limit exceeded` (controls too), even after the 15f second public node; `eth_call` / `eth_getCode` / `eth_blockNumber` fail ~1 in 3 with `no provider available`, a 6-try retry gets through. Use state getters (e.g. `lastHarvestTime()`) for "nothing in 7 days" | scout 9a729ceb (11-18 20:40Z, scout lane 305,900/300,000) |
| base | `A maximum of 10 addresses is allowed`; `exceed maximum block range: 50000`; blocks older than ~18 days: `HTTP 403 Archive requests require a personal token` | scout 06583cf3, builder 7f9b7ac3 |
| avalanche | `block range too large ... maximum of 100 blocks` (wiki says 10,000: that is the Alchemy cap) | scout 42f8d172 |
| polygon | `HTTP 400 ranges over 10000 blocks are not supported on free plan` even for a 769-block address-less query; later `no provider available` | builder 56e8c1ce, reviewer 4f7118b6 |
| arbitrum | fork at a past block: `HTTP 403 ... personal token`, reads succeed only after 3-30 retries | builder ab638f11 |

Any error text starting `all providers failed: public:` means the read went to a public node.

## What to do

- Scouts: a `public:` error or an empty control = verdict `unclear` with the numbers so far; never `dead_end` on a zero from that hour.
- Builders: do the fork proof first in the session, before scanning; if the lane is spent, prove at head and cover past cases with archive `eth_call` (code override) on `--lane paper`, a handful of calls, not scans (`pitfalls/fork-past-state-public-nodes.md`).
- Bulk log scans stay on the research lane; if it is spent, shrink the work or leave a `leads` row for after 00:00Z.
- The fix that removes the problem (a reserved fork budget, fewer scout reads, or a bigger lane) is the human's: proposed in `inbox/human/` on 2026-11-17 (meta fa898bbe); bsc public getLogs forwarded 2026-11-18 (meta 096358ac).
