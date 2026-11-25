trial: cheap-chain trial bot (decision 2026-11-17-cheap-chain-trials), Morpho Blue cbETH/USDC and WETH/USDC liquidations on Base.

# trial-morpho-eth-base

**What it does.** When a price aggregator behind one of the two markets' oracles updates (CBETH/USD
for cbETH/USDC; ETH/USD or USDC/USD for WETH/USDC), the bot reads that market's 200 borrowers nearest
the liquidation threshold in one Multicall, simulates `TrialMorphoRouteTake.take` for those at or over
it (debt / maxBorrow >= 0.9998) and (live) sends it. The executor calls
`Morpho.liquidate(seized=0, repaidShares)`, sells the seized collateral to USDC along a route of UniV3
pools inside Morpho's callback (cbETH -> WETH on the 0.01% pool -> USDC on the 0.05% pool; WETH -> USDC
on the 0.05% pool), lets Morpho pull the repayment, and reverts `NoProfit()` unless its USDC balance
grew by `minProfit`. No flash loan, no principal: the wallet holds gas only. Gain goes to the bot
wallet as USDC. It does not touch the cbBTC/USDC market (that is `trial-morpho-cbbtc-base`).

## Last 7 days of competition (ledger `morpho_blue.liquidate` to 2026-11-17 02:40Z, attempts:1549)

| | cbETH/USDC `0x0ca10126...` | WETH/USDC `0x8793cf30...` |
|---|---|---|
| Liquidate events / txs | 549 / 489 | 744 / 157 |
| Distinct takers | 65 | 39 |
| Repaid | 1.10M USDC | 7.63M USDC |
| Tickets under 1,000 / under 100 USDC | 447 / 335 | 444 / 286 |
| Top takers | 0x20f63594... 72 txs (283 USDC in total), 0xdbc48be5... 54, 0x4fe15238... 45, 0xba277aa7... 27 | Atlas batchers 0x9cbb82b9... 252, 0xed989ee2... 130, 0x91d68269... 122 (504 of 744) |
| Blocks from the oracle update to the take (10-tx sample each) | 0 for 8, then 2 and 522 | 0 for 8, then 2 and 152 (that one crossed later than its last ETH/USD update) |
| Priority fee | same-block takers 1.5-440 gwei (gas = 50-80% of the bonus); later takers 1.2-2.6 gwei | same-block 1.1-15 gwei (Atlas 15); the +2-block taker 0.1 gwei |
| Gross per take | 7.41% of repaid at the oracle price, minus 0.06% pool fees and the cbETH pool's price | 4.38% of repaid minus 0.05% |

Sample rows with hashes: `scratch/trial-morpho-eth-base/competition-7d.json`. Paid-above-gas example:
tx `0xf89904ba...` (block 57519279, 7.00 USDC repaid, gas 0.044 USD, bonus about 0.31 USD, 2 blocks
after the ETH/USD update). Base fee 0.005-0.012 gwei: an attempt at the base fee costs about 0.005 USD.

The bot arrives about 1 s after the update log (feed delivery), i.e. 4-5 Base blocks late, and its fee
cap is below what the same-block takers pay. It can win only what they leave (4 of the 20 sampled
takes were 2 or more blocks late). That share is what the trial measures.

## Send condition (bot.py `attempt`)

- simulate the exact calldata with `eth_call`; gross = returned USDC gain;
- ETH is valued at the WETH market oracle's own price x 1.15 (4,000 USD until first read);
- priority fee = 40% of gross at most; `maxFeePerGas = min(fee cap, 2 x gasPrice + priority)` with
  fee cap = (0.95 - 0.03 USD L1 allowance) / ETH value / 550,000 gas (about 0.80 gwei at ETH 1,820);
- gas cap = 550,000 x maxFeePerGas at that ETH value + 0.03 USD; always < 1 USD;
- send only if gross > gas cap; `minProfit` = gas cap, so the executor enforces it too;
- size: the whole debt up to 4,000 USDC (cbETH, thin first hop) or 150,000 USDC (WETH), one retry at 1/8;
- a signer rejection is final; 600 s cooldown per borrower (20 s if Morpho says healthy).

Every send logs `send_result` with `result` won/lost, `gas_used`, `gas_cost_wei` (L2 + L1 fee),
`winner_block`, `send_block`, `blocks_after_winner`.

## Reads

- feed: one filter, `/logs/base?address=<0x05c84a58...,0x68be4c50...,0x71e021bc...>&topic0=<AnswerUpdated>,<0x8d530b9d...>`
  (measured 181 + 199 AnswerUpdated/day on the cbETH and ETH aggregators over the last 100,000 blocks,
  the USDC/USD one is rare): about 380 x 35 CU + 4 CU/min = 19k CU/day. On `gap`, a removed log,
  429/503 or a connection error both near sets are re-read through the relay;
- relay: one Multicall `eth_call` (26 CU, 200 nearest borrowers of the market that moved) per update
  (about 380/day = 10k CU), both markets every 420 s as the safety poll (205 x 2 x 26 = 11k CU), a full
  scan of the 3,759 + 7,168 seeded borrowers (55 calls = 1.4k CU, about 15 s) every 6 h or after a 1%
  oracle move but at most every 30 min (4-8/day = 6-11k CU). About 27-32k CU/day, hard cap 70,000 in code.
- Total about 46,000-51,000 CU/day = 0.024-0.027 USD/day at 1M CU = 0.53 USD.

## Limits known at placement

- Borrowers are seeded from the Morpho API at placement (debt >= about 0.9 USDC); a borrower who opens
  a position later is not seen until the seed file is refreshed. Refresh weekly if the trial continues.
- Health uses stored totals (interest since the market's last update is not included), so the bot
  simulates everything from ratio 0.9998; the simulation is the gate, not the ratio.
- cbETH's UniV3 depth is thin (0.01% pool: 7.4 cbETH + 11.6 WETH at placement). Larger cbETH takes are
  cut to 4,000 USDC of debt; if the pool moves away the simulation fails and nothing is sent.
- The fork proof's "healthy" guard used a borrower with no position at the reset block (Morpho answers
  'position is healthy'); a real healthy debtor's revert is shown by the self-test (0x1c8d5cf2... at
  block 57997286) through `eth_call`.
- Positions that cross by interest accrual only are seen by the 420 s safety poll, not by the feed.

## Files

`bot.py` (all logic), `run.sh`, `seed-borrowers.json`, `executor-runtime.hex` (paper code override =
`eth_getCode` of the fork deployment, proof.py writes it). Executor source and proof:
`scratch/trial-morpho-eth-base/` (`contracts/src/TrialMorphoRouteTake.sol`, `proof.py`,
`proof-result.json`, `selftest.py`).
