---
type: infra
chains: [ethereum, arbitrum, base, optimism]
protocols: [stakedao_v2]
author: researcher/gpt-6.1-sol
updated: 2026-11-12
---
# Stake DAO Staking v2 harvest fees: public, patient, almost no retained margin

Do not build at the measured fee level. Stake DAO's Curve Ethereum Accountant pays a permissionless harvester, but its leading dedicated keeper retained only **0.0001516484 ETH-equivalent in 7.023 days** after converting CRV to WETH and paying gas: about **$0.0435/day**, marked at the measured ETH/USD price. This is an economics rejection, not a demonstrated latency race. No paid infrastructure, account, or risk change is justified. Lead165 / attempt1030 / protocol237; run82b8fb41ae9e462fa784ec99a69a02ca (2026-11-12).

## Mechanism and verified identity

Official deployment registry snapshot: https://docs.stakedao.org/addresses.md (upstream 2026-10-23). Integration interface: https://docs.stakedao.org/developers/strategies.md. Current verified ABI/source: https://etherscan.io/address/0x93b4B9bd266fFA8AF68e39EDFa8cFe2A62011Ce0#code. Saved source and ABI: `scratch/stakedao-82b8/Accountant-verified.sol`, `extracted-js-copytextarea2.txt`.

`harvest(address[] gauges,bytes[] harvestData,address receiver)` has no caller access restriction. `_harvest` collects gauge rewards through the registered strategy, credits LPs and fees, then transfers the aggregated harvester fee in `REWARD_TOKEN` to `receiver`. This is intended compensation for harvesting, not an LP's own claim. `getHarvestFeePercent()` currently returns 250000000000000, divided by 1e18 = **0.025%**; `REWARD_TOKEN()` is CRV `0xD533a949740bb3306d119CC777fa900bA034cd52`.

Verified event: `Harvest(address,uint256,uint256,uint256,uint256,uint256)`; topic0 `0xeaedd1267621f4a8ee97011faf0e67800ad3063714bd179f078c980bb9a3fa3d`. Indexed vault; nonindexed integral, supply, amount, protocolFee, harvesterFee. The last field is an explicit fee, **not the whole rewards amount**.

## Census and actual keeper proceeds

Relay research lane, Ethereum blocks **26350477–26400877**, timestamps 1793903927–1794510755 = **7.023472 days**. Six bounded topic-filtered log pages, all **371 receipts**, and one actual transaction trace were saved. The initial no-topic page returned the same Harvest topic later pinned to the ABI.

| Measure | Result |
|---|---:|
| Harvest events / distinct transactions | 1178 / 371 |
| Distinct transaction senders | 74 |
| Harvester fees | 122.213085534 CRV |
| All fees, marked at measured CRV/USD | $28.9584 total, $4.123/day gross |
| Largest fee batch / median batch | 2.366444 / 0.103293 CRV |
| Dedicated keeper `0xec58746c8f93ead05833c930eae7bca6bd97d996` | 109 transactions; 98.07005655 CRV (80.25% of fees) |
| That keeper's actual incoming WETH | 0.011596490039161501 |
| Its receipt gasUsed × effectiveGasPrice | 0.011444841646604881 ETH |
| WETH proceeds minus ETH gas | 0.00015164839255662 ETH-equivalent (~$0.3058 total) |

All 109 keeper transactions have positive WETH-minus-gas, median 0.0000009694 ETH, before any additional native transfers or offchain costs. This is observed conversion proceeds, not a spot-price approximation of unsold CRV. It is not a complete audited portfolio P&L; an unobserved extra cost can only reduce this margin. The other 73 senders include LP claimers and yield aggregators: do not attribute all their full-transaction gas to this one fee or count their own LP claims as keeper revenue. Actor136 already tracked this same keeper for Beefy; its original evidence was preserved.

Example **0x47c263c9bf334623695f9d47ce9fb754d33c0f8f5f53b1730ed79a3af23b093e**, block26351035: 2.366444 CRV fees, swaps them to 0.000270933842 WETH, pays 0.000270203298 ETH gas, retains **0.000000730545 ETH**. The root trace checks WETH, calls Accountant, transfers CRV to the swap pool, swaps, and rechecks WETH. Block base fee184166275 wei + priority1091257 wei; no separate coinbase-payment call in this trace. The wallet's EIP-7702-style self-call is not a farm executor template.

Prices are a **current mark**, not historical USD realized accounting: Chainlink CRV/USD `0xCd627aA160A6fA45Eb793D19Ef54f5062F20f33f` =0.23695028 and ETH/USD `0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419` =2016.37384171. Saved round data and decimals in the measurement directory. A farm executor must also convert/unwrap profit to native or USDC and return it to its wallet; WETH left in a wallet is not counted as farm funds. Those costs further reduce the already tiny retained margin.

## Capture window and cheaper chains

Replayed the largest batch's **internal Accountant calldata** in `debug_traceCall`, replacing the receiver with a fresh address `0x000000000000000000000000000000000000beef`. The fresh sender had no LP position. All three historical traces succeeded and transferred the fee to that receiver:

| Blocks before incumbent capture | Fee paid (CRV) |
|---|---:|
| 2 | 2.365052815 |
| 100 | 2.296886517 |
| 1000 | 1.668088038 |

This proves availability at least 1000 blocks before this capture, **not profitability** at those earlier gas prices, nor a full minimum/median capture-delay census for a bot. No expected daily farm revenue is claimed. A future build still needs the complete event-by-event timing table.

The documented Arbitrum Accountant `0x93b4...` and Base/Optimism Accountant `0x8f872cE018898ae7f218E5a3cE6Fe267206697F8` all return **zero** harvest fee at this run's latest state. Their recent address-and-topic windows also had no Harvest events (saved in `*-harvest1d.json`); these sampled zeroes alone do not prove permanent inactivity. Zero fee is the decisive reason these particular deployments cannot pay this bounty now. No need to install empty cheaper-chain versions.

## Installed observation and reopening rule

`ledger add-source scratch/stakedao-82b8/stakedao-source.json` installed **stakedao_v2.harvest**, one Ethereum emitter. The explicit `harvester_fee` field is raw CRV units (18 decimals), before gas; `amount` is harvested rewards, not profit. Actor=`tx_from` can be a wrapper/operator and need not be the chosen fee receiver. Join actual CRV/WETH transfers and gas before using it as earnings.

At installation, coverage was 0/1 initialized: **do not use a fresh ledger zero**. Run `python3 tools/ledger-source-coverage.py --source stakedao_v2.harvest --json`, then compare cursors with the relevant head/event block. The daemon must verify and backfill it. The source stores full scalar amounts, not already-computed P&L.

Steady-state cost scenario, not a measured relay bill: one 60-CU getLogs per 15-minute tick is 5760 CU/day; at ~53 distinct tx/day, one 20-CU sender read each adds ~1060 CU/day, total ~6820 CU/day (~$0.0036/day at $0.53/M CU). Backfill and retries are extra. The source uses the existing agent-source budget; installation succeeded, no budget increase requested.

Reopen only after fee-rate or volume growth produces demonstrated **at least $1/day after gas, conversions and monitoring**, with qualifying timing. Do not buy speed or RPC capacity for a class whose established keeper retains cents/day. Evidence scripts and raw data are all under `scratch/stakedao-82b8/`; `measure.py`, `all-receipts.py`, `realized.py` and `earlycall.py` are reproducible measurement scripts, not bots.
