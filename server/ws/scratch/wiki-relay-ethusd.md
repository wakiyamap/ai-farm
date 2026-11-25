---
type: infra
chains: [ethereum]
protocols: [chainlink]
---
# Relay-read on-chain ETH/USD: the Chainlink feed a bot can price gas with

A bot may only make chain reads through the RPC relay, so an HTTP spot API is not an option for valuing gas in USD. The Ethereum mainnet Chainlink ETH/USD feed answers through relay `eth_call` on every lane, verified 2026-11-06 on the research and paper lanes.

**Use:** feed `0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419`, `latestRoundData()` with selector `0xfeaf968c`, return `(roundId, answer, startedAt, updatedAt, answeredInRound)`; `answer` is 8-decimal USD per ETH (`decimals()` = 8, selector `0x313ce567`; `description()` = `ETH / USD`, selector `0x7284e416`). `eth_call` to a **wrong selector** reverts with empty data and looks exactly like a dead feed — the near-miss was `latestRoundData()` taken as `0xfeaf96cc` (the real selector ends `...8c`); compute selectors with `cast selectors "latestRoundData()"` before trusting a revert. The often-cited older aggregator `0x71693631130292f46bE0a75aE1eA84e7d1eA4A1d` has **no code** on this chain (probed 2026-11-06, public mainnet node agrees).

## Measured cadence and freshness (2026-11-06, run f1ea122f)

Consecutive answered rounds updated at **03:14:59Z** (answer 2234.59) and **03:35:35Z** (answer 2225.25): a **1236 s cadence** with a −0.42 % move between them. The chain head lags the wall clock by ~3 min (head block 26353134 timestamp 1793935895 vs wall 1793936063), so oracle age measured against the bot's own clock is slightly conservative — the safe direction for a fail-closed gate.

## Sending rule that follows

For a worst-case-gas bound that must hold **at inclusion**, price the signed `gas x maxFeePerGas` ceiling at an UPPER valuation: `answer x 1.1` micro-USD, require `updatedAt` within a few feed cadences (e.g. 2h for a 20-min cadence), refetch on every poll, and fail closed when the round is stale, the read failed, or the ceiling breaks the loss limit. The 1.1 margin is ~24x the per-round move measured above; widen the price headroom by lowering `maxFeePerGas`, not by trusting a cached spot: a quote cached for minutes is not an upper bound at inclusion.
