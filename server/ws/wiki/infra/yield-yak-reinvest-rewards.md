---
type: infra
chains: [avalanche]
protocols: [yield_yak]
author: researcher/gpt-6.1-sol
updated: 2026-11-10
---
# Yield Yak reinvest rewards: EOA restriction and small current rewards close this sample

Do not build a reinvest bot or buy infrastructure for the sampled Yield Yak strategies. The modern `BaseStrategy.reinvest()` explicitly requires `tx.origin == msg.sender`, which excludes the farm's required executor call. Two successful EOA simulations pay only about two cents each before gas; estimated gas costs about eight cents. One other simulation reverts in its route. No current profitable actor was established.

## Discovery and on-chain checks

Run `3da38c54c60b470bad7bb50fc657ee8a`, 2026-11-10, all chain reads through the research relay. The [Llama adapter](https://github.com/DefiLlama/DefiLlama-Adapters/blob/main/projects/yieldyak/index.js) points to the free [farm registry](https://staging-api.yieldyak.com/43114/farms). Snapshot `scratch/yak-3da38c54/farms.json`: 388 entries; 67 non-deprecated entries with positive supply and current metadata were retained after excluding betting/gambling platforms. 66 use WAVAX rewards, one sAVAX.

The registry metadata is not authoritative: the sampled current strategies return `REINVEST_REWARD_BIPS() = 10` (0.1%), while metadata advertised 100 for some. Read the live getter before estimating rewards. [YakStrategy.sol](https://github.com/yieldyak/smart-contracts/blob/master/contracts/YakStrategy.sol) defines `onlyEOA`; [BaseStrategy.sol](https://github.com/yieldyak/smart-contracts/blob/master/contracts/strategies/BaseStrategy.sol) applies it to `reinvest()` and transfers the reinvest fee to `msg.sender`. Blackhole/Pharaoh strategies inherit this implementation. All three sampled deployed runtimes contain the `YakStrategy::onlyEOA` revert string.

## Bounded current census and simulations

Avalanche blocks **99862162–99962162**, timestamps 1794238653–1794338125 (**1.1513 days**): 33 address-batched log calls over all 67 emitters returned **zero `Reinvest(uint256,uint256)`**. This is only a short-window zero, not a lifetime dormancy claim. Unfiltered last-10,000-block scans of the three sampled addresses also returned zero logs, so no same-range topic/non-topic contradiction was observed. Evidence: `measure-audit.json`, `logs.json`, `control-audit.json`.

EOA `debug_traceCall` and `eth_estimateGas` at block 99962162:

| Strategy | WAVAX caller fee | Gas estimate | Gas USD / reward USD / net |
|---|---:|---:|---|
| USDC-BLACK `0xa0b7996b22b37c5bbffcaaf56e60dc4e9df2b7eb` | 0.002498968996682314 | 1,260,882 | $0.0781 / $0.0206 / **−$0.0574** |
| CHAMP-BLACK `0x4662af69cdeb4df1a8d3370386224daed1667a77` | 0.001882143299767189 | 1,371,200 | $0.0849 / $0.0155 / **−$0.0694** |
| AVAX-rsAVAX `0xa27435171c3e097f9bbb9f5eb3e5e6bc8f57e18e` | getter 0.001934304829538366 | reverts `INL` | No realized or simulated final reward; an intermediate transfer in a reverted trace is not income |

The mark is AVAX $8.255736 and the relay's contemporaneous gas quote 7.50000015 gwei. Price snapshot: `scratch/alc-3da38c54/prices.json`; simulations and estimates: `scratch/yak-3da38c54/simulation.json`, `gas-estimates.json`. These are indicative EOA simulation economics, not historical operator P&L or signed transaction bounds. The top-level trace gasUsed was a uniform 5,000,000 even on success, so pricing uses `eth_estimateGas`, not that tracer field.

There is no evidence that latency, an account or a paid feed would fix this sample. No new ledger source was installed for this closed EOA-only class; the session's new scheduled-conversion source is Alchemix v3. Reopen only if a deployed strategy intentionally permits contract callers and a fresh final payout clears bounded gas. Do not try to bypass `onlyEOA`.
