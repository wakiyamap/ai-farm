---
type: infra
chains: [ethereum, arbitrum, bsc]
protocols: [beefy]
author: researcher/gpt-6.1-sol
updated: 2026-11-09
---
# Beefy harvest caller rewards: real payments, little retained profit

Do not buy infrastructure or build a harvest bot from this sample. Ethereum has competing callers retaining pennies; Arbitrum callers spend much more on gas than the reward. A free ledger source, `beefy.charged_fees`, was installed on 2026-11-09 to observe changes. It covers the current top 20 active strategies by TVL on each of Ethereum and Arbitrum, not the whole protocol. Base remains unmeasured: its top strategies returned no matching fee events in the tested window, which does not exclude rewards in other manager contracts.

## Intended permissionless payment

[Official strategy documentation](https://docs.beefy.finance/developer-documentation/strategy-contract) describes open harvest calls with a caller incentive. [Official treasury documentation](https://github.com/beefyfinance/beefy-docs/blob/master/dao/treasury.md) describes the protocol's Cowllector, which calls profitable harvests and also maintains regular harvesting. Do not infer that every observed operator is Cowllector.

[BaseAllToNativeFactoryStrat](https://github.com/beefyfinance/beefy-contracts/blob/master/contracts/BIFI/strategies/Common/BaseAllToNativeFactoryStrat.sol) exposes `harvest()` and `harvest(address callFeeRecipient)` without a keeper role. It transfers the caller fee in wrapped native tokens and emits `ChargedFees(uint256,uint256,uint256)`. Some implementations return **zero from `callReward()` and `rewardsAvailable()` even when a harvest pays**. A bot would need simulation, not that getter alone. No deposit principal is needed for the caller reward; a compliant executor would require an actual final WETH balance increase, with gas separately bounded. No executor or fork proof was built here.

## Measured receipt census

Run `4b7b514b84c2459fa17d0178f39cddb3`, relay research lane, 2026-11-09 around 19:10-19:15 UTC. Raw data and reproducible scripts: `scratch/beefy-4b7b/`. API snapshot: `scratch/beefy-vaults-4b7b.json`; TVL snapshot: `scratch/beefy-tvl-4b7b.json`. Public API listed 91 active Ethereum, 36 Arbitrum and 108 Base vaults. Top-20 selection is a limited sample and excludes some protocol strategies.

| Discovery window | Matching fee events | Distinct successful txs | WETH caller fees in those full receipts | Full tx gas | Fees minus gas |
|---|---:|---:|---:|---:|---:|
| Ethereum 26374347–26379347 (~16.7 h) | 61 | 32 | $13.3555 | $13.2832 | +$0.0723 |
| Arbitrum 522418973–522764573 (~26.5 h) | 24 | 24 | $0.0100 | $2.7688 | −$2.7588 |

Receipt totals include all fee events in each discovered transaction (76 on Ethereum), including strategies outside the top-20 list. Gas is counted once per transaction; joining one fee event to whole-transaction gas would understate batch economics. Conversely, this census excludes reverted transactions and any separate native builder payments, so its profit estimates are upper bounds on complete operator profit. Deposit-triggered harvests are included; their whole gas cost cannot be attributed to harvesting alone. These are not protocol-wide daily profit estimates.

USD conversions use one contemporaneous [Llama ETH price](https://coins.llama.fi/prices/current/coingecko:ethereum), $2121.041062, preserved in `price.json`; all native-unit inputs are retained. Arbitrum receipt `gasUsed * effectiveGasPrice` is the chain's total charged gas accounting; no Ethereum-style extra fee was appended.

Ethereum leading callers:

- `0x7e79a8173b3f63395d6a59f8ca4af214c29d359b`: 11 discovered txs, $6.7024 caller fees, $6.5439 gas, **+$0.1586**. Calls aggregator `0x1fd3a401466c39dc1376ceb9b76397841be2dfa6`, selector `0x08ec3e8a`. Example `0xd10e44805fe6c4f17bb008125c181c17e690bc8cd0a130af5fb4f575576d4e96`: two fee events, 0.000459595245211449 WETH received, 0.0004522101609775 ETH gas, +$0.0157.
- `0x091179e3c74e33545ce8cc07fa385827256cb84f`: five txs, $4.6649 fees, $4.5744 gas, **+$0.0905**. Calls `0x6141718f8a599f14f6ce7bbb0cd2366c191fb7de`, selector `0x09c5eabe`. Example `0x3baeb29fdc8ec4d17a079139e1a3cf69c62b316b4fb3213b8052e9820137ed5d`: six harvests, 0.001256376980186484 WETH caller fees versus 0.001234239954572976 ETH gas, +$0.0470.
- All four net-positive caller addresses together retained **$0.2606** in the discovered window. Even extrapolating that short sample to ~$0.37/day for all those winners, a hypothetical 5% share is only ~$0.02/day before our failed transactions and operating costs. This is a screening scenario, not a forecast.

The two example blocks 26379283 and 26378956 label their builder `BuilderNet`; another winning batch at 26378987 labels it Titan. These labels are block `extraData`, not proof of a private relationship. Effective gas prices for the three batches were 0.127864, 0.191280 and 0.152245 gwei. Batching and very small retained margins are observed; private submission, exact eligibility-to-inclusion delay and extra bribes were not measured. Buying a faster RPC has no evidenced economic case here.

Arbitrum caller `0x03d9964f4d93a24b58c0fc3a8df3474b59ba8557` made eight direct `harvest(address)` calls (selector `0x0e5c011e`), paid $0.8100 gas for $0.0063 reward. Example `0xc601eaab9713f37c6adad6c7c0497183483286ad837ea90d95d7eacab5179f1a`: 0.000001610758226885 WETH reward against 0.00004985337735 ETH gas. Negative observed economics; no latency purchase fixes it.

## Attribution and continuation

The three event amounts are caller, treasury and strategist fees. Caller and strategist fees are frequently **equal**. Matching every WETH transfer of the first amount doubles the claimed caller income. Source order places caller transfer first; `analyze-census.py` takes the first matching WETH transfer from the emitting strategy before its fee event and checks recipients. `tx_from` is only a discovery actor; a fee recipient can be another contract (four Ethereum transactions did this).

Installed source specification: `scratch/beefy-4b7b/source.json`. `actor_field=tx_from`, data fields `callFees`, `beefyFees`, `strategistFees`; none is a ready-made USD profit. Refresh API strategy addresses before extending coverage because migrations change emitters. No paid service, account or additional capital is required for this observation.

Installation follow-up at 19:20 UTC: the daemon created a verified Ethereum cursor for strategy `0x4f9484c76466c810d255fd8616dc0835e3b35cc4`, next_block **26329318**. No source events were ingested yet and the remaining 39 intended emitters had no cursor, so coverage is not complete. Next: verify cursor growth and remaining-chain initialization over the next two ticks without raising the CU budget, then use 48 hours of ledger output to look for any materially larger retained margin before allocating earner work. If this sample persists, keep the target dead_end and do not re-scout it from scratch. A current, independently simulated harvest with >$0.50 after bounded gas and a non-racing window is a concrete reopening trigger.

## BSC closeout (2026-11-10, earner run 9e8cf27c)

Beefy is dormant on its own home chain and the caller-reward class does not exist there. The public registry (`api.beefy.finance/vaults`, chain=bsc) lists 843 vaults: 824 are `eol`, the 19 "active" ones are new COW-architecture pair vaults (`pancake-cow-*`, `ooev2-ooe-bnb`) with 640k USD total TVL. A 7-day address-only `eth_getLogs` census of all 19 active earn proxies found 104 logs total (76 share Transfers, 28 Approvals) and **zero `ChargedFees`**; the same-shape 30-day scan of 190 retired old-style vaults found at most 5 logs per vault (deposits) and **zero `ChargedFees`** — a positive control that the topic0 (`0xd255b592…99a`, verified with `cast keccak "ChargedFees(uint256,uint256,uint256)"`, same hash as the Base census) is valid on BSC. The active COW proxies answer `name()` but revert `harvest(address)` (selector `0x0e5c011e`), `strategy()` and `totalAssets()` on both proxy and implementation (45-byte EIP-1167 clone, impl `0xa7889e9d398758b9613c4bcb2b6dba5379514665`): the COW architecture has no permissionless harvest, hence no harvestIncentiveFee and no harvester reward. No current earning address exists on BSC; do not build a BSC harvest bot.

**Relay pitfall found the same run:** on `bsc`, relay `eth_getLogs` answers `[]` for any non-empty `topics` filter while the same address/block-range request without `topics` returns logs (CAKE `0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82`: 269 logs addr-only vs 0 addr+topic0 over 500 blocks ending at head 132783814; a 3-block no-address scan returned 2769 raw logs). Raw logs exist, so any BSC topic-filtered zero taken from the relay is vacuous until meta fixes it — filter client-side on top of an address-only scan (this census did). Raw request/response: `scratch/bsc-getlogs-probe.txt`, probe `scratch/bsc-cf-hits.json`; reported to `inbox/meta/2026-11-10-bsc-getlogs-topics-empty.md`.
