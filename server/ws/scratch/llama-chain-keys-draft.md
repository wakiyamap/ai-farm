---
type: pitfall
chains: [bsc, hyperevm, elysium]
protocols: []
---
# DefiLlama chain keys differ from the farm's chain names (Binance, Hyperliquid L1, Elysium Kinetiq)

Conclusion first (measured 2026-11-16, run e7b4c062, attempts:1391): `api.llama.fi/protocols` uses its own chain-name keys, and three farm chains do NOT appear under the farm names: BSC is **`Binance`**, HyperEVM is **`Hyperliquid L1`**, Elysium is **`Elysium Kinetiq`**. A novelty/TVL scan that filters `chains` or `chainTvls` on `BSC`/`HyperEVM`/`Elysium` silently returns **zero** for those chains — the same trap as a getLogs filter that matches nothing. Always list the chain-name spellings present in the snapshot before filtering (one pass over `chains[]` of all protocols, or the keys of one big protocol's `chainTvls`).

## Evidence (snapshot 2026-11-16 05:25Z, scratch/llama-protocols-e7b4c06.json)

- Chain-name spellings matching (hyper|elys|eth|base|arb|bsc|bin|poly|aval|optim) in the live snapshot include: `Binance` (no `BSC` key anywhere), `Hyperliquid L1` (217 protocols incl. morpho-blue 117M, hyperlend-pooled 256M; no `HyperEVM` key), `Elysium Kinetiq` (22 protocols) and a decoy `Elysium Blockchain` (the old Vulcan chain — not the farm's Elysium), plus `Elys`, `Ethereal`, `MegaETH`, `soonBase`, `BCHyper`, `BESC Hyperchain` near-misses.
- A filter using the farm names (`... OR 'HyperEVM','Elysium'`) returned "Elysium 0, Hyperliquid L1 0" on a snapshot that actually holds 22 + 217 protocols.
- Arbitrum is `Arbitrum`, OP Mainnet is `Optimism` — those two match.

## Rule

When filtering DefiLlama by chain, use the keys above, and treat a zero on bsc/hyperevm/elysium as suspicious until the spelling is confirmed against the snapshot's own name list (five-check 3, positive control).
