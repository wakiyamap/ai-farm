trial: BIM Yield Aero gauge harvest caller reward on Base.

The single routed strategy is `0xBFeF6e2FE9E866Ddc0E7929ddb6CFB6E15313Bd3`. Its verified source exposes `harvest(address)` and `callReward()`.

## Competition, last 8 days

Eight harvests in blocks 56,094,147-59,118,154, all sent by EOA `0x558079b5f12b9c8d6119bfa5e7b7a58ba05dc579`, exactly 24 h apart at 15:00:05 UTC, each with a 0.001 gwei priority fee. Transaction indexes 12, 27, 29, 63, 91, 124, 145: this is not the OP Stack index-1 race. Nobody else called it. The reward was already quoted at 9.27e12-10.84e12 wei 1,800 s before each capture and 9.48e12-11.06e12 wei at the parent block (`scratch/trial-bim-harvest-base/competition.json`, each hash and fee). Blocks to take: the incumbent is a timer, so any block before 15:00:05 UTC in which gross > our cap.

## How it sends (fixed 2026-11-18 after review)

The trial checks only from 14:15 to 15:10 UTC, every two minutes:

1. `callReward()` and the latest block's base fee. `maxFeePerGas` = base fee x 1.03 + 100,000 wei tip (refused above 10m wei). Base fee moved at most 1.6% in 5 s over the 1,024 blocks before the 11-18 harvest (`scratch/bimfix/feehist.json`).
2. If the quote clears a rough pre-filter: `eth_estimateGas` of `take(...,1)`, gas limit = estimate x 1.10 (refused above 2.4m). The strategy's swap has a gas-reserve check (`InsufficientGasForCall`), so the limit must sit well above gasUsed: at block 59,118,153 the estimate is 1,615,441 while gasUsed is 1,444,790, and a fixed 1.6m limit reverts (reviewer, `scratch/review-51c3/bim-gas.json`).
3. cap = gas limit x maxFeePerGas + 100e9 wei L1 allowance (largest of the incumbent's L1 fees: 27.3e9 wei). Send only if the simulated payout at exactly that gas limit is above the cap, with `minProfit = cap + 1` simulated again.
4. Priority fee: a fixed 100,000 wei per gas (about the 5th-percentile tip of included Base transactions), passed explicitly because the signer turns 0 into maxFee/10. About 1.8e11 wei per send, at most 2% of gross.

Hard ceiling per send: 2.4m gas x 10m wei + allowance = 2.41e13 wei, 0.096 USD at 4,000 USD/ETH. Typical cap 9.4e12 wei (0.04 USD). A lost attempt cost 7.9e12 wei on the fork.

## Does the margin survive the corrected limit?

`scratch/bimfix/est.py` (relay reads at each harvest's parent block, executor as code override; `corrected-cap-harvests.json`):

| harvest block | estimate | limit | cap wei | gross wei | send |
|---|---|---|---|---|---|
| 56,094,147 | 1,526,837 | 1,679,520 | 8.918e12 | 9.731e12 | yes |
| 56,526,147 | 1,490,409 | 1,639,449 | 8.791e12 | 9.480e12 | yes |
| 56,958,147 | 1,704,719 | 1,875,190 | 9.964e12 | 9.832e12 | no |
| 57,390,148 | 1,589,248 | 1,748,172 | 9.293e12 | 1.0247e13 | yes |
| 57,822,147 | 1,560,408 | 1,716,448 | 9.111e12 | 1.0869e13 | yes |
| 58,254,151 | 1,585,537 | 1,744,090 | 9.397e12 | 1.1065e13 | yes |
| 58,686,147 | 1,678,843 | 1,846,727 | 9.795e12 | 1.0441e13 | yes |
| 59,118,154 | 1,609,914 | 1,770,905 | 9.435e12 | 1.0992e13 | yes |

7 of 8 pass. The fixed bot's own `check()` replayed at past blocks (`scratch/bimfix/check_at_block.py`): `paper_sim success` at 59,118,153 and at 59,100,000 (one hour earlier), skip at 56,958,146. Expected net per win is about 3.7e12 wei, or about 0.0067 USD at the measured 1,811 USD/ETH price; the 4,000 USD/ETH reference elsewhere is a conservative loss-cap conversion. The trial measures the win rate against a timer keeper.

At 2026-11-19 14:15:01 UTC, the supervised paper service logged a fresh `paper_sim success` before the usual 15:00:05 incumbent take: gross 10,793,330,150,860 wei, signed gas cap 8,851,414,000,000 wei, estimated gas 1,515,397, limit 1,666,936, max fee 5,250,000 wei. Source: `logs/bot.jsonl` at `ts=1795097701.292`. This is a simulation against the current head, not a broadcast or realized profit.

## Fork proof

`python3 scratch/bimfix/proof_fix.py` (leases and releases the shared Base fork; `proof-fix-result.json`): reset to parent block 59,118,153, deploy the artifact, fund the owner; guard revert `0x1f2205ee…71d2` (NoProfit, owner -7.937e12 wei); success `0xb767e579…0c90` at limit 1,776,985 and maxFee 5,254,087 wei with `minProfit = cap + 1`, 1,444,790 gas, owner +3.665e12 wei net; executor WETH and ETH zero afterwards. The original proof (`scratch/trial-bim-harvest-base/proof.py`) used a 2,000,000 limit.

## Reads

28 daily window checks x (one 26-CU `eth_call` + one 20-CU `eth_getBlockByNumber`) = 1,288 CU/day; worst case each check also estimates and simulates twice (72 CU): 3,304 CU/day, 0.0018 USD/day at 0.53 USD per million CU. The code stops at 20,000 CU/day. No per-block polling, no feed.

## Logs and closing

Every check, opportunity (with `gas_estimate`, `gas_limit`, `max_fee_wei`), skipped send, paper simulation and real send (`send_result`: won/lost, gas used, winner block) is in `logs/bot.jsonl`. Live mode uses the signer and `EXECUTOR_ADDR_BASE` or `EXECUTOR_ADDR`. After seven live days or when the 5 USD gas budget is spent, count sends, wins and net ETH after `gasUsed * effectiveGasPrice + l1Fee`. A zero-win result closes this thin route.
