---
type: infra
chains: [any]
protocols: []
---
# Farm reaction time R per chain (race rule): measured table 2026-11-15

**Status (earner run 44446bcc, 2026-11-15, lead 192 human request).** R(chain) = **feed detection p90 + send-to-inclusion median**, measured as the lead specified. Detection is a live measurement (one modest event per chain, farm-feed `/logs` long-poll + a relay poll at 10 s, 40 min window, 15:32–16:12 UTC). Send-to-inclusion exists for **one ethereum send only** (the farm's whole live-send history); every other chain gets the lead's estimate **detection + one block time**, marked *(est)*. Where the sample behind a number is thin (n < 20), meta's 20-sample rule (decision 2026-11-14-race-rule-seconds item 19) still applies: treat that chain's R as provisional and keep classifying with **R = 3 s** until the human accepts the table.

## The table (2026-11-15, run 44446bcc, 40 min probe)

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

Avalanche's 0.00: arrival falls inside the same integer second as the (second-granularity, ~0.92 s cadence) block timestamp. Polygon's negative p90: PoS block timestamps run ~1 s ahead of the wall clock at delivery; the definition is kept as written, so polygon detection is effectively "immediate at second granularity".

A 10 s-polling bot's R = poll p90 + send: ethereum ~21 s; other chains est poll p90 + one block (polygon ~10 s, avalanche ~14 s, optimism ~12 s, elysium ~11 s, base ~6.2 s).

## Against the 3 s placeholder

Lead's rule: only a chain with a measured R may deviate; until then 3 s stays.

- **ethereum: R ≈ 11.6 s, worse than 3 s** (feed p90 3.50 s measured on 219 events; the 8.06 s send→inclusion is n = 1 — the farm's only live send). Ethereum is the one chain where the placeholder is optimistic against the farm: its earliest block is T + 11.6 s ≈ the second block after the event. Blocked-for-speed ethereum closings get stronger, not weaker; no verdict changes.
- **polygon, avalanche, optimism, elysium: est R ≈ 0.9–2.2 s, all below 3 s** (detection measured on 85–900 events each; send is the lead-sanctioned one-block estimate; none has 20 send samples). No blocked_infra lead on any of these four chains exists to re-classify, so nothing changes today; if the human accepts the estimates, sub-3 s R makes feed bots on these chains better than assumed, not worse.
- **base, arbitrum, bsc: thin detection (5–7 events, est R ≈ 0.8–1.6 s), send est.** base is the only chain with blocked-for-speed leads (13, 170, 21: liquidation races) — their closure stands on the human's liquidation-class decision anyway, and base R is an estimate; listed in `inbox/meta/2026-11-15-reaction-time-table.md` for the human.
- **hyperevm: no sample at all** (Felix Redemption emitted 0 times in 49 min). Estimate only: R ≈ 2.0 s (feed delivery ~1.0 s per `infra/feed.md` + one block 0.98 s), marked estimate.

The dominant term the 3 s placeholder ignores is **send→inclusion (8.06 s on ethereum, n=1)**, not detection: farm feed detection is ≤ 3.5 s p90 on every sampled chain. Re-measure send→inclusion when more chains have live bots: the signer's response arrives before inclusion, so bots must log both the send wall time and the receipt's block timestamp; so far only morpho-nextblock-ethereum logged a send (once).

## How each number was taken

- **Feed detection**: one modest event per chain, subscribed through farm-feed `/logs` from a process on this host; latency = local arrival wall time − the log's `blockTimestamp`. Events (all verified to emit on-chain in the same run, rate-tested over 300–10000 blocks first): ethereum Aave v3 pool `0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2` event topic0 `0x804c9b842b2748a22bb64b345453a3de7ca54a6ca45ce00d415894979e22897a` (address taken from the ledger's aave_v3.liquidation source for ethereum, same run; ~250/h verified over 300 blocks; event name not pinned — 4byte lookup failed); base `0x000000008a8330b5d1f43a62bf4c673a49f27ba0` / arbitrum `0xb274d5f4b833b61b340b654d600a864fb604a87c` / bsc `0x00000000a55e50c71b70db3c8b58749cd1e18eb2` UniswapX reactor `Fill(bytes32,address,address,uint256)` (addresses from `scratch/uniswapx.fill.json`; ~26/17/14 per h); polygon `wPOL 0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270 Deposit` (name() read on-chain); avalanche `WAVAX 0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7 Deposit` (name() read on-chain); optimism `WETH 0x4200000000000000000000000000000000000006 Deposit` (name() read on-chain); hyperevm Felix `Redemption(uint256,uint256,uint256,uint256,uint256)` on the 3 CDPs from `scratch/felix_cdp.redemption.json`; elysium configured-USDC `0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65 Transfer` (~1.7k/h — the only event with enough volume on a 6-day-old chain; borderline "busy", see caveats).
- **Poll detection**: same events via relay `eth_getLogs` every 10 s (the interval our bots really use: `bots/paper/bold-redeem-tail-ethereum/bot.py POLL_S=10`; the live gearbox/morpho bots are feed-driven); latency = poll return wall time − event block timestamp (block ts fetched and cached per block through the relay). This is what a 10 s-polling bot gets: median ≈ half the interval + provider lag.
- **Send-to-inclusion**: bot hands the tx to the signer → timestamp of the including block. The farm's complete history of such pairs is the one live send recorded in any bot log: morpho-nextblock-ethereum `pool_init_sent` 2026-11-14T14:02:38.942Z, tx 0xdf25a9c7…, included in block 26413695 (ts 1794664967 = 14:02:47): **8.06 s, n = 1**. The gate's deploy/fund txs have inclusion blocks but no hand-time stamps readable from the workspace (the farmgate journal is not group-readable: "No entries" for our user), so they contribute no samples. Archive bot logs (31 bots) contain no send-with-txhash lines either.
- **One-block-time estimates** measured this run over 2000 blocks each: base 0.20 s, elysium 0.31 s, arbitrum 0.31 s, bsc 0.45 s, avalanche 0.92 s, hyperevm 0.98 s, polygon 1.50 s, optimism 2.00 s, ethereum 12.0 s.
- Probe: `scratch/rt_probe/probe.py` (raw `feed_<chain>.jsonl`, `poll_<chain>.jsonl` under that directory), summary `scratch/rt_probe/stats.py`. Relay lane: research. Feed CU added during the 40 min: ~12k of the 700k/day budget (elysium USDC Transfer was the heaviest at ~2.7k; per-filter caps not approached).

## Caveats

- Detection windows are one 40-minute slice of one day; feed delivery can vary with Alchemy websocket lag. The ~1.0 s figure of `infra/feed.md` is reproduced (p50 0–2 s across chains); elysium/ethereum are at the top of that range.
- Elysium's filter is a USDC `Transfer` stream (the only ≥1/h modest event found there); per the feed rules a busy Transfer stream is acceptable for an infra probe but would be a reviewer `fix` inside a bot.
- Send→inclusion has n=1 on its only chain, and it measured a pool-init setup tx, not a trading send; `8.06 s` includes waiting for the next ethereum block (12 s cadence), so it is mostly "wait for block", which is why chains with sub-second blocks should have much lower send→inclusion — but nobody has measured it there.
- The negative polygon latencies are real under the lead's definition (delivery wall time − block timestamp); they reflect PoS timestamp rounding, not clock skew: the host clock was verified through the ethereum feed samples (ethereum feed p50 2.02 s ≈ the canonical ~1 s delivery + processing, same as `infra/feed.md`).

## Previous content (meta 85c0c080, 2026-11-15): the 1-sample ethereum note

**Status then: provisional, not yet "measured"** — decision 2026-11-14-race-rule-seconds item 19 asks for at least 20 samples per chain; until a chain has 20, keep classifying with **R = 3 s**.

| # | UTC | chain | bot | ts → feed | ts → send | included | source |
|---|---|---|---|---|---|---|---|
| 1 | 2026-11-14 14:02:35 | ethereum | morpho-nextblock-ethereum | 1.9 s | 3.9 s | next block (26413695) | bots/live/morpho-nextblock-ethereum/logs/bot.jsonl, tx 0xdf25a9c7… |

That sample's feed leg (1.9 s) is consistent with this page's ethereum feed distribution (p50 2.02 s); the 3.9 s ts→send included ~2 s of scan/simulate decision time; the send→inclusion leg is the 8.06 s figure in the table above. Note the sent tx was the executor's pool-init setup tx, not a liquidation (`pitfalls/executor-setup-at-startup.md`), and the incumbent taker in the same opportunity landed earlier in the same block (index 56 vs 169, priority fee 0): landing in the next block does not mean landing ahead of it.
