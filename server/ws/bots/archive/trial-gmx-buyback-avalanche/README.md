trial

# trial-gmx-buyback-avalanche

Cheap-chain trial (decision 2026-11-17): measure by sending whether the farm can take a GMX v2 fee-buyback batch on
Avalanche. Not a liquidation. Capital 10 USD of AVAX for gas; the principal (150 WAVAX) is a Balancer flash loan.

## Mechanism

GMX v2 `FeeHandler` (`0x1A3A103F9F536a0456C9b205152A3ac2b3c54490`, gmx-io/gmx-synthetics `deployments/avalanche`,
source `contracts/fee/FeeHandler.sol`) sells the protocol's accrued fees to anyone:

- `claimFees(market, feeToken, 2)`: public, moves a market's accrued fees into the FeeHandler's available amount.
- `buyback(feeToken, buybackToken, minOutputAmount, oraclePrices)`: public. The caller pays one batch of the buyback
  token (150 WAVAX) and receives `min(available, batch value at the oracle price x 1.006)` of the fee token (USDC).
  The 0.6 pct is `maxPriceImpactFactor(WAVAX) 0.4 pct + maxPriceImpactFactor(USDC) 0.2 pct` from the DataStore.
- Prices are Chainlink Data Streams reports passed in the call, at most 30 s old (`BUYBACK_MAX_PRICE_AGE`).

So the pot fills as fees accrue (or gains value as AVAX falls), and once it is worth more than a batch plus costs,
taking it pays up to 0.6 pct of about 1,060 USD, minus the 0.05 pct swap fee and gas.

The farm has no Data Streams key. GMX keepers publish the same signed reports in the calldata of every order they
execute, so the bot copies the WAVAX and USDC reports from the newest **confirmed** keeper transaction and passes them
with the FeeHandler oracle's provider (`0x236913dB...`). `scratch/trial-gmx-buyback-avalanche/lifttest.py` shows the
FeeHandler accepts them (and refuses the keeper's own provider address, as a control).

## What the bot does

1. Every 300 s (60 s when the pot is within 10 pct): `FeeHandler.getOutputAmount` over 8 markets (the uncapped pot)
   and `slot0` of the Uniswap V3 WAVAX/USDC pool `0xfAe3f424...`. Estimated gain = pot (capped) sold at the pool
   price minus the batch.
2. Estimated gain above 0.05 AVAX: every 6 s, `eth_getLogs` on the GMX EventEmitter (`OraclePriceUpdate`) over the
   last 40 blocks, fetch the newest keeper tx, parse its reports. Reports older than 20 s: wait for the next keeper tx.
3. Fresh reports: simulate the executor call, estimate gas, and send only if the simulated gain exceeds
   `gasLimit x maxFeePerGas`; `minProfit` = that cap + 1 wei. Paper mode logs `paper_sim` instead of sending.

Executor `GmxBuybackTake` (one transaction): Balancer flash 150 WAVAX, `claimFees` on the markets, `buyback`, sell the
USDC on the pool, repay, revert `NoProfit` unless the WAVAX balance grew by `minProfit`, unwrap, pay the bot AVAX.

## Competition, last 8 days (600,000 blocks to 100,739,657)

| block | taker (executor / EOA) | tx index | priority fee | USDC out | pot had held that amount for |
|---|---|---|---|---|---|
| 100,168,006 | 0x72448e59 / 0xa35854d1 | 5 | 1 nAVAX | 1,224.06 (whole pot) | at least 37 s |
| 100,316,166 | 0x72448e59 / 0xa35854d1 | 4 | 1 nAVAX | 1,131.36 (cap) | at least 153 s |
| 100,449,225 | 0x72448e59 / 0xa35854d1 | 1 | 1 nAVAX | 1,072.57 (whole pot) | at least 2,692 s |
| 100,672,141 | 0xd3693064 / 0x360de77e | 9 | 1 nAVAX | 1,062.83 (cap) | at least 61 s |

Four takes, two operators, both with their own report source (their reports were 9 s old and not copied from a keeper
tx). The newest take kept 0.897 WAVAX (6.3 USD) for 2,133,988 gas x 8.57 nAVAX = 0.018 AVAX (0.13 USD). For the two
whole-pot takes the trigger was the AVAX price, not the pot, so their "held for" time overstates the takeable window;
the two cap-bound takes sat at the full premium for 61 s and 153 s. Blocks to take: 80-150 after the pot crossed.
Keeper txs carrying both reports: 192 in 49,699 s, median gap 105 s, p90 658 s (`scratch/gmxfee/avax2.py`).

The same mechanism on Arbitrum is a same-block race (32 of 32 USDC takes crossed the threshold inside the block they
were taken in, `scratch/gmxfee/windows.py`); no bot there.

## Fork proof

`python3 scratch/trial-gmx-buyback-avalanche/proof.py` (reset to 100,672,140, the parent of take `0x2c36270a...`):
success `0xd026b0c3...` owner +0.878 AVAX net of gas (gain 0.897320294 WAVAX, the capture's own number); guard
`0xaa2ae20f...` NoProfit; repeat `0xb8c54e38...` NoProfit(0); non-owner `0x3468094a...` NotOwner. Details in the manifest.

## Read cost

Idle 2 calls per 300 s = 15,000 CU/day; near 2 calls per 60 s; armed about 165 CU per 6 s. Code cap 90,000 CU/day =
0.048 USD/day at 0.53 USD per million CU. No feed filter.

## Logs (`logs/bot.jsonl`)

`start`, `params`, `check` (pot, price, estimated gain, state), `no_reports`, `reports_stale`, `simulate_revert`,
`skip_gross_below_cap`, `skip_gas_cap`, `opportunity`, `paper_sim`, `send`, `send_result` (won / lost, gas used,
winner block and tx), `signer_reject`, `read_budget`, `error`.

## Limits

- The bot waits for someone else's keeper tx to carry the reports; with gaps of minutes it loses to a taker with its
  own report source whenever that taker is awake. A Chainlink Data Streams key would remove the wait (lead row).
- If GMX changes the FeeHandler oracle's provider, `simulate_revert` shows the oracle error and nothing is sent.
