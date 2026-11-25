---
type: infra
chains: [any]
protocols: []
---
# Chain selection: which new chain to add, Alchemy-supported candidates scored on the human's 5 tests (in progress)

Working table for `decisions/human/2026-11-13-chain-selection.md`. Researchers fill it in across sessions; the final report goes to `inbox/human/<date>-chain-selection.md` (Japanese). Seeded by meta 2026-11-12 with structure only: every cell below is 未確認 until a researcher writes a sourced number. Never fill a cell from memory.

## Scope

- Candidates: every EVM mainnet on Alchemy's official supported-chains page that the farm does not have (no testnets, no non-EVM). Record the page URL and fetch date here when you take the list.
- Comparison rows: the current 9 farm chains (KB / wiki numbers allowed).

## Tests (human thresholds are guidelines; say if one drops a promising chain)

1. Money at stake: lending borrows >= 50M USD, or 30-day liquidation repaid >= 1M USD
2. Slow blocks: >= 2 s
3. Not sold: main protocols' price-triggered liquidations are not sold via an oracle auction (Chainlink SVR, Atlas, ...)
4. Not monopolised: top address < 80% share on the main liquidation protocol (30 d)
5. Alchemy WebSocket (`eth_subscribe`) supported

## Columns per chain

borrows USD + top 3 lenders (+30 d liquidations count/repaid) | non-liquidation payouts >= 1k USD/month | block time s | ordering (FCFS sequencer / fee / priority auction, doc link) | rights sold? | top-1 share | Alchemy HTTP / WS / debug / trace | gas token, Chainlink native/USD feed, USDC issuer + decimals | tests 1-5 | sources

## Table

| chain | borrows | non-liq payouts | block s | ordering | sold? | top-1 | Alchemy | gas/USDC | 1 | 2 | 3 | 4 | 5 | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (candidates: add rows) | | | | | | | | | | | | | | |

### Current farm chains (comparison)

Known from the farm prompts: polygon and hyperevm have no `trace_*` on Alchemy; elysium refuses `debug_*`/`trace_*` and has 100-200 ms blocks; base and optimism are OP Stack. Everything else 未確認 here.

| chain | borrows | non-liq payouts | block s | ordering | sold? | top-1 | Alchemy | gas/USDC | 1 | 2 | 3 | 4 | 5 | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ethereum | | | | | | | | ETH / USDC 6 | | | | | | |
| base | | | | | | | | ETH / USDC 6 | | | | | | |
| arbitrum | | | | | | | | ETH / USDC 6 | | | | | | |
| optimism | | | | | | | | ETH / USDC 6 | | | | | | |
| bsc | | | | | | | | BNB / USDC 18 | | | | | | |
| polygon | | | | | | | no trace | POL / USDC | | | | | | |
| avalanche | | | | | | | | AVAX / USDC | | | | | | |
| hyperevm | | | | | | | no trace | HYPE / USDC | | | | | | |
| elysium | | | 0.1-0.2 | | | | no debug/trace | HYPE / USDC 6 | | × | | | | common.md |

## Progress log

- 2026-11-12 meta: page created (structure only). Next: take the Alchemy chain list, then DefiLlama borrows per chain (`https://api.llama.fi/v2/chains` gives TVL only; borrows are probably the `<Chain>-borrowed` keys of `chainTvls` in `https://api.llama.fi/protocols`; verify on one known lender before relying on it).
