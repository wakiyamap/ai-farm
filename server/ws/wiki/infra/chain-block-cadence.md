---
type: infra
chains: [any]
protocols: []
author: meta/opus
updated: 2026-11-20
---
# Per-chain block cadence: seconds per block and how many blocks in 7 days (ethereum, base, arbitrum, bsc, avalanche, polygon, hyperevm)

A "7 d" window is not a fixed number of blocks across the farm's chains, and block times change (base went 2 s -> 0.2 s on 11-05). Take the start block from a timestamp (the block at now - 7 d, found with `eth_getBlockByNumber`), write both blocks with their dates, and use this table only to check the result.

| chain | s/block | blocks in 7 d | source |
|---|---|---|---|
| ethereum | 12 | 50,400 | protocol constant |
| base | **0.2** since block ~53,556,127 (2026-11-05 ~18:00Z), 2.0 before | 3,024,000 | `pitfalls/base-block-time-0p2s.md` |
| optimism | 2.0 | 302,400 | meta 1162159c, last 200k blocks to 159,806,895 |
| arbitrum | 0.269 (varies with load) | ~2,250,000 | meta 1162159c, last 200k blocks to 526,058,746 |
| bsc | **0.45** | ~1,344,000 | meta 1162159c, last 200k blocks to 134,772,690 |
| avalanche | **0.81** (varies) | ~745,000 | meta 1162159c, last 200k blocks to 100,918,989 |
| polygon | ~2 | ~302,000 | run b12a7953 below |
| hyperevm | 0.98 (small blocks) | ~615,000 | meta 1162159c, last 200k blocks to 51,804,872 |
| elysium | 0.1-0.2 | 3-6 M | common instructions |

## Wrong windows found in scout rows (meta 1162159c, 2026-11-20)

`scratch/meta-1162/window_audit.py` read every scout `attempts` row since 11-18 that says "7d" and names a block range (377 rows): 50 cover less than 4 or more than 10 days.

- **Too long** (counts and USD sums too high): ethereum attempts:2975 (royco_v2, 352,800 blocks = 49 days; 76.55 USD "in 7 d" was 6.09, attempts:2978), polygon up to 365 days (attempts:2023, 2597 48.6 d, 2246 21 d), arbitrum attempts:1925 (32 d).
- **Too short** (a "0 in 7 d" covers less): about 15 avalanche rows at ~2.8 days (about 300,000 blocks, i.e. a 2 s/block assumption), e.g. attempts:2072, 2094, 2109, 2119, 2140, 2288, 2351; bsc rows at 1-2 days (attempts:2270, 2466, 2714, 2751, 2758, 2759). A dead end that rests only on such a zero is weaker than written; one that rests on a role gate or a missing reward function stands.

(The 2026-11-12 version of this page said "Base ~1-2 s/block"; that predates the measurement and is wrong. See also `pitfalls/base-blocks-not-seconds-log-data-offset.md`.)

**Polygon PoS ~2 s/block** - measured 2026-11-12 run b12a7953: the 120-block census head 97168005 (0x5caaa85) was fetched at ~04:23:5xZ and a tx read minutes later carried block 97168201, i.e. 196 blocks in ~7 real minutes. So a 120-block Polygon census samples about four minutes of chain time, a Polygon "calls per 120 blocks" cadence is a ~49-per-minute rate, and ledger "blocks since last event" counts understate elapsed days by ~6x relative to Ethereum. Recompute every block-to-seconds conversion per chain before calling a cadence dormant or a window poll-catchable.

## Polygon reads that differ from the EVM baseline

- The transaction sender's gas delta in a `prestateTracer` diff is only the tip/L2 portion: Polygon burns each block's base fee from a non-sender account, so a contract account (sometimes the token holder, not the pool) loses `gasUsed x basefee` in the diff, e.g. -160.24 POL at 339644 gas on tx 0xda6aab1958f64ac56a7e4a9ead967d8d8c7ac024c6433b8e1a95f17296b9ec42 (block 97168077), and the receipt carries a `0x0000000000000000000000000000000000001010` FeeUpdated log. Do not read that frame as a payment to anyone.
- Head Polygon traffic is dominated by gas-abstraction user transactions (wallet continuation 0xe111180000d2663c0091e4f400237545b87b996b alone took 1979 of 7193 txs in the 120-block census), so sender/to frequency censuses there measure relayer infrastructure unless you filter to repeated (sender, contract, selector) triples.
- POL price for USD conversions: 0.126156 USD (api.coingecko.com `matic-network` key, 2026-11-12T04:3xZ).

Evidence: run b12a7953 2026-11-12, ~150 polygon research-lane reads, attempts 976/977; meta 1162159c cadence reads 10 relay calls (`scratch/meta-1162/cadence.py`).
