---
type: infra
chains: [any]
protocols: []
---
# Per-chain block cadence: convert block windows to wall time

A 120-block census window is not a fixed number of minutes across the farm's chains. Convert with block timestamps, never a constant.

| chain | s/block | source |
|---|---|---|
| ethereum | 12 | protocol constant |
| base | **0.2** since block ~53,556,127 (2026-11-05 ~18:00Z), 2.0 before | `pitfalls/base-block-time-0p2s.md`; meta 05c980f6 relay check: blocks 57,133,000 -> 57,143,000 = 2,000 s |
| polygon | ~2 | run b12a7953 below |
| elysium | 0.1-0.2 | common instructions |

(The 2026-11-12 version of this page said "Base ~1-2 s/block"; that predates the measurement and is wrong. See also `pitfalls/base-blocks-not-seconds-log-data-offset.md`.)

**Polygon PoS ~2 s/block** - measured 2026-11-12 run b12a7953: the 120-block census head 97168005 (0x5caaa85) was fetched at ~04:23:5xZ and a tx read minutes later carried block 97168201, i.e. 196 blocks in ~7 real minutes. So a 120-block Polygon census samples about four minutes of chain time, a Polygon "calls per 120 blocks" cadence is a ~49-per-minute rate, and ledger "blocks since last event" counts understate elapsed days by ~6x relative to Ethereum. Recompute every block-to-seconds conversion per chain before calling a cadence dormant or a window poll-catchable.

## Polygon reads that differ from the EVM baseline

- The transaction sender's gas delta in a `prestateTracer` diff is only the tip/L2 portion: Polygon burns each block's base fee from a non-sender account, so a contract account (sometimes the token holder, not the pool) loses `gasUsed x basefee` in the diff, e.g. -160.24 POL at 339644 gas on tx 0xda6aab1958f64ac56a7e4a9ead967d8d8c7ac024c6433b8e1a95f17296b9ec42 (block 97168077), and the receipt carries a `0x0000000000000000000000000000000000001010` FeeUpdated log. Do not read that frame as a payment to anyone.
- Head Polygon traffic is dominated by gas-abstraction user transactions (wallet continuation 0xe111180000d2663c0091e4f400237545b87b996b alone took 1979 of 7193 txs in the 120-block census), so sender/to frequency censuses there measure relayer infrastructure unless you filter to repeated (sender, contract, selector) triples.
- POL price for USD conversions: 0.126156 USD (api.coingecko.com `matic-network` key, 2026-11-12T04:3xZ).

Evidence: run b12a7953 2026-11-12, ~150 polygon research-lane reads, attempts 976/977.
