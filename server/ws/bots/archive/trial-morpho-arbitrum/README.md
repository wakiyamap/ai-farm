trial: Morpho Blue WBTC/USDC and WETH/USDC liquidations on Arbitrum (cheap-chain trial, decision 2026-11-17-cheap-chain-trials)

# trial-morpho-arbitrum

Liquidates borrowers over the line in two Morpho Blue markets on Arbitrum One
(MorphoBlue `0x6c247b1F6182318877311737BaC0844bAa518F5e`, lltv 0.86, incentive 4.38%):

| key | market id | collateral | oracle | sale pool (UniV3 0.05%) |
|---|---|---|---|---|
| wbtc | `0xe6392ff1...e99169` | WBTC `0x2f2a2543...` | `0x88193fcb...` (WBTC/BTC x BTC/USD / USDC/USD) | WBTC/USDC `0x0e4831319a50228b9e450861297ab92dee15b44f` |
| weth | `0xca83d02b...d8642c` | WETH `0x82af4944...` | `0x282feb10...` (ETH/USD) | WETH/USDC `0xc6962004f452be9203591991d15f6b388e09e8d0` |

One transaction through the executor `TrialMorphoArbTake` (deployed by the gate, owner = bot
wallet): `Morpho.liquidate` hands over the collateral, the callback sells it to USDC on the
pool, Morpho pulls the repayment, the rest is paid to the bot wallet as USDC. It reverts
`NoProfit` unless the USDC gain is at least `minProfit` (= the send's gas cap), so a lost
attempt costs gas only. No principal, no flash loan.

## Competition, last 7 days (blocks 522728582-525148582, attempts:1885)

18 Morpho liquidations on Arbitrum by 12 senders; 7 in these two markets:

| block | market | repaid USDC | sender | blocks from oracle update to take | tx index (update / take) | priority fee gwei |
|---|---|---|---|---|---|---|
| 523779845 | weth | 8.73 | 0xcd4e58c2... | 0 | 1 / 22 | 0.027 |
| 523779865 | wbtc | 9,975.26 | 0x04f57ab7... | 0 | 5 / 6 | 0.038 |
| 524202074 | weth | 159.30 | 0x04f57ab7... | 0 | 2 / 3 | 0.038 |
| 524268505 | wbtc | 38,695.14 | 0xbd985202... | 0 | 2 / 3 | 0.038 |
| 524279951 | wbtc | 748.97 | 0x64959f1a... | 0 | 40 / 42 | 0.038 |
| 524280430 | wbtc | 20,740.52 | 0xa8ed1b7f... | 0 | 35 / 36 | 0.038 |
| 524318530 | wbtc | 2,180.71 | 0xc789b135... | 0 | 51 / 52 | 0.038 |

All 7 were taken in the block of the Chainlink update that made them takeable, right behind
it (through contracts `0xd90bc01d...` and `0x10d1b4a5...`). Blocks to take: 0 in every case.
This bot reads the update from the feed and lands 4-12 blocks (1-3 s) later, so in this
sample it would have won nothing; the trial measures whether anything is ever left (on Base,
4 of 20 takes in the same class were later than the update block). When it is late its
simulation reverts and nothing is sent, so being late is free. Gross at stake in the 7 days:
4.38% of 72,309 USDC repaid = about 3,170 USD; one attempt costs 0.02-0.05 USD of gas.

Not covered: the WBTC/USDT0 and WETH/USDT0 markets (3 takes; the gain would be USDT0, not
USDC), GLV, PT-USDai, thBILL and XAUt0 collateral.

## How it runs

- Feed `/logs/arbitrum`: `AnswerUpdated` (`0x0559884f...`) on the aggregators
  `0xa8c2ad8fc02733d758c0585478cdf6c53d6c9cb8` (BTC/USD), `0x97aae9dac7c4a649f54c00a29aaa8a140616dc50`
  (WBTC/BTC) and `0xd827123d014578c965f6c9d87a641ec05faa5501` (ETH/USD). The answer is topic 1
  of the log: a market is re-read only when its price is a new low since the last timer read.
- A read = one Multicall3 `eth_call`: oracle price, market totals, `position()` of the 200
  borrowers nearest the line. Timer read of both markets every 600 s; also on `gap` and feed errors.
- Full scan of `seed-borrowers.json` (267 + 95 borrowers with debt, from Morpho's public API on
  2026-11-17, each checked on-chain by the scan) every 6 h or after a 1% price move. The seed is
  static: borrowers who open a position after 2026-11-17 are not seen until it is refreshed.
- A borrower at debt/maxBorrow >= 0.9998 is simulated through the executor (`eth_call`), the gas
  limit comes from `eth_estimateGas` x 1.30, the bid is at most 40% of the simulated gross, and the
  send goes out only if gross > gasLimit x maxFeePerGas and that cap is under 1 USD.
- Logs: `logs/bot.jsonl` (`start`, `feed`, `scan`, `opportunity`, `opportunity_skip`,
  `simulate_revert`, `paper_sim`, `send_result` with won/lost, gas used, winner block).

## Read cost (live)

- Feed: about 1,880 logs/day x 35 CU + 4 CU/min = 71,500 CU/day.
- Relay: new-low reads about 560/day x 26 = 14,600; timer reads 144 x 2 x 26 = 7,500; full scans
  4-8 x 3 x 26 = 300-600. About 22,500 CU/day, hard cap 26,000 in code.
- Total about 94,000 CU/day = 0.050 USD/day at 1M CU = 0.53 USD (under the 100,000 trial limit).

## Proof

`scratch/trial-morpho-arb/proof.py` (fork, both markets, guards) and
`scratch/trial-morpho-arb/selftest.py` (the bot's own paper path on the fork and at head);
hashes and deltas are in the manifest's `fork_evidence`.
