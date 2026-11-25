# Flat Money Arbitrum graduation

This bot graduates `trial-flatmoney-arbitrum`, promoted on 2026-11-17 and live for 126.9 hours at the 2026-11-23 11:11 UTC check. It executes a public announced Flat Money order after the protocol's five-second delay, takes the fixed WBTC keeper fee, sells that fee to WETH, unwraps it, and returns native ETH to the bot wallet in one transaction. No principal is used. The trial stays live until the human stops it after this grad is promoted.

## Live record and decision

Source: `bots/live/trial-flatmoney-arbitrum/logs/bot.jsonl`, `scratch/grad-flatmoney-fees.json` (13 receipts and inclusion blocks through the relay), and `grad-candidates.py` at 2026-11-23 11:11 UTC.

| Measure | Trial result |
|---|---:|
| Sends / wins / lost sends | 13 / 13 / 0 |
| Gross before gas | 0.001132496901265182 ETH |
| Gas paid | 0.000361711167210385 ETH |
| Net at receipt prices, in ETH | 0.000770785734054797 ETH |
| Gate-funded / wallet value now | 9.56 / 10.85 USD |
| Net since promote at current wallet valuation | +1.29 USD in 126.9 h, about 0.244 USD/day |

Two more announcements yielded `order_result: not_takeable` after 12 simulations each; no one executed them. They were not lost sends and no gas was paid. The raw error begins `0xe3835a27`; the trial has no evidence that increasing a fee or sending faster would make those orders executable. The 13 sends have `send_result: won`, winner block equal to send block, receipt status 1 (checked first `0xceb6f419...` and last `0x4e7ad548...`), and 0 blocks behind the winner. The bot sent 0.54–1.60 seconds after executable time in the log. A fee increase has no measured benefit; this grad keeps the trial's fee settings.

The reward is fixed per order (199–262 sat WBTC in the prior seven-day census, `attempts:1835`). More capital cannot increase it. Capital stays at 10 USD, `max_loss_per_tx_usd` at 1 USD; a 2x/5x size run would not apply to this fixed keeper fee. The historical 45 takes were from EOA `0x45d83e658e2f70ba83e4e519f792f065c4a01d7d`, blocks 522693627–525113627, at 2–6 seconds after takeable, median 11 blocks in the sampled timing table, priority fee zero (`scratch/trial-flatmoney/timing.json`).

## Winning fee shares

Every row below is a trial win. Share = `(receipt effectiveGasPrice - inclusion block baseFeePerGas) × gasUsed / simulated gross native gain`. Builder payments from this executor are zero: `FlatOrderKeeper.sol` has no coinbase transfer. `scratch/grad-flatmoney-fees.py` produced the full hashes and fee data in `scratch/grad-flatmoney-fees.json`.

| Winning tx | Block | Index | Priority / gross |
|---|---:|---:|---:|
| `0xceb6f419` | 525349071 | 1 | 13.22% |
| `0x363fa7be` | 525349243 | 3 | 13.12% |
| `0x230f2910` | 525475127 | 7 | 13.26% |
| `0x9092c366` | 525475280 | 1 | 13.16% |
| `0xd562fe05` | 525635854 | 1 | 13.25% |
| `0x530198e0` | 525636003 | 2 | 13.22% |
| `0x61e9ff45` | 525769172 | 1 | 13.25% |
| `0x9317e941` | 525769325 | 1 | 13.22% |
| `0x08089b49` | 525859135 | 1 | 12.53% |
| `0x652b1a6d` | 525860834 | 1 | 12.49% |
| `0x82c389c5` | 525862185 | 1 | 12.22% |
| `0x3b01cf5b` | 525889059 | 1 | 13.03% |
| `0x4e7ad548` | 525890371 | 1 | 13.03% |

Median 13.16%, middle half 13.03–13.22%, maximum 13.26%. Historical rival priority was zero (45 transactions in `scratch/trial-flatmoney/timing.json`); its observed timing was slower than the trial's 13 wins. The code's `BID_SHARE=0.20` limits priority to 20% of simulated gross; actual priority cost was 12.22–13.26% because gas used was below the 1.30× estimated gas limit. This retains the trial's proven setting and stays below the 50% ceiling. Total gas consumed 31.94% of gross. There is no fee increase in this grad.

## Transaction guard and fork proof

`FlatOrderKeeper.run(module,account,update,feeToken,pool,weth,minProfit)` is owner-only. It calls `executeOrder`, swaps only the newly received WBTC fee on UniV3, unwraps WETH, reverts unless native gained by at least `minProfit`, and pays the whole native balance to the bot wallet. Its callback accepts only the pool active for this transaction. The bot sets `minProfit` to the signed gas cap and sends only if gross exceeds that cap. `gasLimit = eth_estimateGas × 1.30`; the fee cap is the lesser of 0.95 USD (ETH price from Hermes with 15% allowance, or a 4000 USD fallback) and 90% of simulated gross. The signer enforces the 1 USD signing-time loss limit. Deployment artifact: `scratch/trial-flatmoney/contracts/out/FlatOrderKeeper.sol/FlatOrderKeeper.json`, unchanged from the trial.

Rerun `python3 scratch/trial-flatmoney/proof.py` (fork lease, reset to Arbitrum block 525070833, deploy, fund, guard, success, release). The 2026-11-23 UTC rerun gave success tx `0x24d245c1933d37e8639dbdc42498313ae5f563db6923373dfd98c2d087fe278e`: 231 sat WBTC converted, +82,602,606,487,086 wei to the owner before gas, executor WBTC/WETH/native zero. `NoProfit` reverted at `0x2a357efa79237ef3703020d9881ed127734656c7d7c3ee34ce97145b9e33b3b2`; a second take reverted `OrderInvalid` at `0x7ca92f6ce719516d76a413a14ec9c4f1fa897a2078e4889264c392b0e233407a`. The proof confirms the selector and calldata against `cast`. `executor-runtime.hex` is the fork deployment's `eth_getCode` for paper simulation only.

`python3 scratch/grad-flatmoney-selftest.py` reran the copied bot's paper `handle()` against that same fork state: gain 82,602,606,487,086 wei, estimated gas limit 1,315,603, cap below 1 USD, then a live Hermes read and relay safety reread. The fork reset took about 23 wall-clock seconds, so that script's `sim_s_after_executable` is a test-harness delay, not a measured mainnet race time.

## Feed, read cost, and dependency

`OrderAnnounced` topic `0x0aaed4f1864bd4663319a4a0ceb0b5f0766e7e58ee27cf50c48232258d5f582c` on `0x2326bb21b769d81e134c9b305ca156f989249fe7` is the feed filter. An order is executable five seconds after its announce block timestamp. The bot waits, fetches a fresh signed WBTC/USD update from the local Hermes proxy, then simulates and sends. On feed gap or error, and every 600 seconds, it checks the last 280 Arbitrum blocks. Last trial send was at log timestamp 1795167632.86 (2026-11-20); next announcement is unscheduled.

Expected read cost: about 6,000 feed CU/day plus 14,000 relay CU/day (144 safety polls × 85 CU = 12,240; roughly seven orders × 250 CU = 1,750). About 20,000 CU/day costs 0.011 USD/day at 0.53 USD per million CU. The code caps relay reads at 60,000 CU/day. Hermes reads do not use Alchemy CU. All relay reads, including startup and result reads, are inside the bot's budget handler.

**Dependency:** the farm's Hermes key is a trial ending about 2026-12-02. Public keyless Hermes returned HTTP 401 from this host (`wiki/pitfalls/pyth-hermes-needs-key.md`); only 2 of 45 historical orders had a third-party onchain Pyth update fresh enough to omit the blob. After expiry, this keeper cannot reliably execute most orders until the human provides a paid or otherwise durable price-update route. This dependency is sent to `inbox/meta/` for forwarding. If Hermes returns 401, the bot logs the error and sends nothing.
