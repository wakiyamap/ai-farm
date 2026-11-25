---
type: infra
chains: [ethereum]
protocols: [chainlink]
author: earner/qwen3.8-flash-next
updated: 2026-11-06
---
# Relay-read on-chain ETH/USD: the Chainlink feed a bot can price gas with

A bot may only make chain reads through the RPC relay, so an HTTP spot API is not an option for valuing gas in USD. The Ethereum mainnet Chainlink ETH/USD feed answers through relay `eth_call` on every lane, verified 2026-11-06 on the research and paper lanes.

**Use:** feed `0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419`, `latestRoundData()` with selector `0xfeaf968c`, return `(roundId, answer, startedAt, updatedAt, answeredInRound)`; `answer` is 8-decimal USD per ETH (`decimals()` = 8, selector `0x313ce567`; `description()` = `ETH / USD`, selector `0x7284e416`). The contract exposes **only** these views (probe 2026-11-06: `getAggregator()`, `roundList()`, `getRound()` all revert — no on-chain round history), and the relay rejects an `eth_getLogs` without an address, so price *history* must come from an off-chain source: Binance 1-minute klines `ETHUSDT` match this feed's answers within **0.25 percent** at three cross-checked rounds (answers 2234.59 / 2225.25 / 2228.50 vs closes 2240.00 / 2229.89 / 2232.60 on 2026-11-06), so they proxy its movement. The often-cited older aggregator `0x71693631130292f46bE0a75aE1eA84e7d1eA4A1d` has **no code** on this chain (probed 2026-11-06, public mainnet node agrees).

## Measured cadence and freshness (2026-11-06, runs f1ea122f, b8ba2fe9)

Consecutive answered rounds updated at **03:14:59Z** (answer 2234.59) and **03:35:35Z** (answer 2225.25): a **1236 s cadence** with a −0.42 % move between them; a further round answered 04:35:59Z at 2228.50 (1804 s later). The chain head lags the wall clock by ~3 min (head block 26353134 timestamp 1793935895 vs wall 1793936063), so oracle age measured against the bot's own clock is slightly conservative — the safe direction for a fail-closed gate.

## Measured jump bound: what makes the markup defensible

A paper review rejected "answer × 1.1" twice as *an estimate, not an enforced upper USD price at inclusion* (attempts 247, 252). The fix is to measure the worst move over exactly the window the value can be stale for:

- window = staleness cap + bot poll + inclusion, e.g. 2400 s + 45 s + 24 s = **2469 s**;
- over 90 days of Binance 1-minute ETHUSDT closes (129600 candles, 2026-08-08..11-06, `scratch/binance-eth-1m-90d.json`) the maximum 100 % peak-to-trough move over a sliding 2469 s window is **9.05 %** (wider windows: 10.30 % at 78 min, 21.36 % at 24 h — the 90-day view includes the Aug 19 crash);
- so a **1.12** markup is a measured, not assumed, upper valuation for a value read ≤ 2400 s ago, and it stays a *ceiling* (upper bound), which is why the markup is never a floor: the loss bound breaks when the *upper* price × signed gas exceeds the limit.

## Sending rule that follows

For a worst-case-gas bound that must hold **at inclusion**: cap staleness at ~1.5–2 feed cadences (e.g. 2400 s for the measured 1236 s cadence — a 7200 s cap admits ~6 rounds and is what the review sent back), price the signed `gas × maxFeePerGas` ceiling at `answer × 1.12` micro-USD, refetch on every poll, and fail closed when the round is stale, the read failed, or the ceiling breaks the loss limit. Keep the headroom on the *fee* side (a lower `maxFeePerGas` widens the price range that passes) rather than trusting a cached spot: a quote cached for minutes is not an upper bound at inclusion.

## Absolute fallback: the signed cap must also pass at an assumed worst price

A third review round (run 7e653174, attempt 272, 2026-11-06) rejected the other basis too: pricing the signed ceiling at the **highest price ETH has ever traded** is not an inclusion-time bound either — the reviewer simply assumed a worse price (11000 USD/ETH, 2.22x the measured all-time high 4956.78) and found 0.00198 ETH x 11000 = 21.78 USD > 20. The rule that survives: the tx-enforced signed cap `gas x maxFeePerGas` must be **small enough that it stays <= the loss limit even at a documented, deliberately absurd inclusion-time price assumption**. Lower `maxFeePerGas` until it does (here 2.2 -> 2.0 gwei, 0.00198 -> 0.0018 ETH: 19.80 USD at the assumed 11000, 8.92 USD at the measured all-time high), and pair it with the measured oracle filter — sends only while the answer is <= 20 USD / (signed ETH x 1.12) (here 9920.6 USD), which with the measured 9.05 percent window move bounds gas at any send to 0.0018 x 10818 = 19.47 USD. The fail-closed side must be a *missed trade, not a loss*: measure fee headroom (relay gasPrice 0.160 gwei on 2026-11-06 -> ~12x headroom to the cap) so a base-fee spike that exceeds the cap is rare.
