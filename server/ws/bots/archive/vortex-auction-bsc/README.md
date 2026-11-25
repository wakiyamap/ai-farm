Scheduled take, not a trial: buys the BNB lot of Bancor's CarbonVortex on BSC when its Dutch auction falls 3 pct under the market price (expected about 2026-12-02 12:07Z).

# vortex-auction-bsc

## What it does

CarbonVortex on BSC (`0x5bCA3389786385a35bca14C2D0582adC6cb2482e`, bancorprotocol/carbon-contracts
`deployments/bsc/CarbonVortex.json`, `version()` 5) holds 0.951886 BNB (about 514 USD) and sells it for
Binance-Peg ETH through the public `trade(token, targetAmount, maxInput)`. The price started at the maximum when
the auction was reset (block 128,378,231, ts 1792333673) and halves every 12 h (`priceDecayHalfLife()` 43,200 s).
At block 135,042,772 (2026-11-22) the ask was 1,295,825 times the PancakeSwap V3 ETH/WBNB price: 20.3 halvings,
10.15 days, from the market price. The bot waits for that time and takes the lot once the ask is 3 pct under the
pool price, in one transaction:

1. flash swap: the PancakeSwap V3 ETH/WBNB pool sends the ETH the auction asks for;
2. `Vortex.trade(native, lot, ask)`: the Vortex pulls the ETH and sends the BNB;
3. the executor wraps what the pool is owed and pays it in WBNB;
4. the rest is sent to the bot wallet as native BNB; the call reverts unless that is at least `minProfit`.

No principal: the wallet pays gas only.

## Why there is a window (who took the past lots)

Every Vortex log in BSC blocks 105,042,186-135,042,154 (155 days; `scratch/rsv390/vortex_hist.py`, priced by
`vortex_disc.py` with coins.llama.fi historical prices). One operator took everything: EOA
`0xfefe5cb7929ef5a4c128ca2fda64c56fd4429b05` through contract `0xc7dd38e64822108446872c5c2105308058c5c55c`
(selector `0xd0c8ea36`).

| block | time (ts) | lot | paid | worth | margin left to the taker | gas | time under the market when taken |
|---|---|---|---|---|---|---|---|
| 105,285,057 | 1781936457 | 0.3874 BNB | 0.13105 ETH = 225.90 USD | 226.46 USD | 0.57 USD = 0.25 pct | 0.03 USD | about 3 min |
| 107,463,891 | 1782917456 | 0.2044 BNB | 0.06293 ETH = 100.54 USD | 112.22 USD | 11.68 USD = 10.4 pct | 3.12 USD (10 gwei) | about 1.9 h |
| 109,969,564 | 1784045643 | 4.1276 BNB | 1.0283 ETH = 1,926.75 USD | 2,404.52 USD | 477.77 USD = 19.9 pct | 0.02 USD | about 3.8 h |

(The last column is 12 h x log2(1 / (1 - margin)): the ask loses 5.6 pct an hour.) Windows from "3 pct under the
market" (the bot's line, 32 min after the market price is crossed) to taken: lot 1 was taken before the line
(the bot would have lost it), lot 2 about 4,900 s later, lot 3 about 11,900 s later. Median 4,900 s, minimum:
taken before the line. On BSC (0.45 s blocks) that is not a race; the farm's reaction time (R = 3 s) does not
decide it, the choice of the line does. A token lot (USDT, block 116,163,447) went at 0.67 pct.

## Expected value

- Dated: one lot, 0.951886 BNB. At the 3 pct line the fork take paid the owner +0.028455 BNB (about 15.4 USD)
  after gas. Two of the three past native lots were still there at that line.
- History at the 3 pct line: 3.4 USD (lot 2) + 72 USD (lot 3) = 75.5 USD in 155 days = 0.49 USD/day. That is
  under the 1 USD/day floor; over the next 10 days the dated lot is worth about 1 USD/day at 2 of 3. The reviewer
  decides whether a dated take of this size deserves a slot. Lots come from Bancor arbitrage fees on BSC, and the
  last native trade was 4 months ago: there may be no lot after this one.
- Risk to the date: any `execute()` that brings new BNB fees into the Vortex while the lot is under
  `minTokenSaleAmount` (10 BNB) resets the auction to the maximum price (another 45 days). The bot then logs a
  far-away `eta_utc` again. A BNB/ETH move shifts the time by 12 h per factor 2 (1 pct = 10 min).

## Guards

- Executor `VortexBuyer.run()`: owner-only, reverts `NoProfit` unless its native balance grew by `minProfit`
  (0 refused), `InputTooHigh` when the auction asks more than `maxInput`; the pool is repaid inside the swap
  callback or the swap reverts; callback accepted only from the pool of this call.
- Bot: gas limit = estimate x 1.2 + 50,000 (refused above 800,000), gas price = 2 x `eth_gasPrice`, never above
  1 gwei and never above the price at which gasLimit x gasPrice reaches 0.90 USD; sent only if the simulated gain
  is at least 5 x that cap; `minProfit` = 90 pct of the simulated gain.
- Worst case of one send: gas, at most 0.90 USD (typical 0.00005 BNB = 0.03 USD at 0.05 gwei x 2).

## Read cost

One look = 3 `eth_call` (78 CU). Far from the date the bot looks every 6 h (312 CU/day); it halves the remaining
time at each look, about 12 more looks on the last day; under the line it looks every 60 s with about 10 calls
(260 CU) until the lot is gone. Typical 300-1,500 CU/day = under 0.001 USD/day at 0.53 USD per million CU; code
cap 20,000 CU/day, then it sleeps to 00:00 UTC. No feed use (nothing to subscribe to: the price moves with time).

## Files

- `bot.py`, `run.sh`, `executor-runtime.hex` (eth_getCode of the fork deployment, paper code override only).
- Executor source `scratch/vortex-auction-bsc/contracts/src/VortexBuyer.sol`, proof `scratch/vortex-auction-bsc/proof.py`,
  self-test `scratch/vortex-auction-bsc/selftest.py`.
- Live: `EXECUTOR_ADDR_BSC` or `EXECUTOR_ADDR` (no fallback).

## Logs (`logs/bot.jsonl`)

`start`, `check` (`ask_above_line` with `eta_utc`, `ask_under_line`, `no_lot`), `opportunity`, `opportunity_skip`,
`paper_sim`, `send`, `send_result` (won / lost, gas used), `signer_reject`, `read_budget`, `loop_error`.
