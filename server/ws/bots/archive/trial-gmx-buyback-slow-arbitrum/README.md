trial

# trial-gmx-buyback-slow-arbitrum

Cheap-chain trial (decision 2026-11-17): take GMX v2 fee-buyback batches of the **slow fee tokens** on Arbitrum. Not a
liquidation. Capital 10 USD of ETH for gas; the principal (1.5 WETH) is a Balancer flash loan. Mechanism:
`wiki read mechanisms/gmx-v2-fee-buyback.md`.

## Why this is not lead 294's race

USDC and WBTC pots are taken by five flash executors inside the block they cross. Every other fee token is left to two
inventory EOAs that call the FeeHandler directly, days late:

| fee token | takes in 30 d (to block 525,514,766) | taker | how long takeable |
|---|---|---|---|
| USDC | 104 | flash executors | same block (lead 294) |
| WBTC | 17 | flash executors | 0-4 blocks |
| USDG | 12 (blocks 525,321,631-525,325,105) | EOA 0xbd7927ef x11, 0x86fe53a6 x1, direct, tx index 1-7 | pot was 9.3 batches 7 days earlier, 12.2 at the first take |
| LINK | 2 | 0x86fe53a6 direct x1, flash executor x1 | not measured |
| WAVAX (0x565609fA) | 2 | 0xbd7927ef direct | above one batch for 7+ days; no pool on arbitrum, not configured |

Sources: `scratch/gmxpots/buybacks-arbitrum-30d.json`, `windows-arbitrum-other.json`, `slow.json`. Priority fees: none
(base-fee gas, 0.02 gwei). One USDG batch through this bot's route at the parent block of the first take: +0.004512 WETH
(8 USD) for about 4.8M gas x 0.02 gwei = 0.17 USD (`sim-relay-result.json`, `selftest.py`).

## What the bot does

1. Every 900 s: `FeeHandler.getOutputAmount` (uncapped pot) for each token in `config.json`; pool prices hourly, or every
   round once a pot is within 10 pct. Estimated gain = pot (capped at batch x (1 + premium)) at the pool price - batch.
2. Estimated gain above 0.0006 WETH: every 8 s for at most 15 min, `eth_getLogs` on the GMX EventEmitter
   (`OraclePriceUpdate`, topic2 = fee token or WETH) over the last 120 blocks, fetch the newest keeper txs, parse their
   reports. Reports older than 20 s: wait for the next keeper tx. No usable report in 15 min: that token rests 2 h.
3. Fresh reports: simulate the executor call, estimate gas, send only if the simulated gain exceeds
   `gasLimit x maxFeePerGas`; `minProfit` = that cap + 1 wei. Paper mode logs `paper_sim` instead of sending.

Keeper txs carrying a USDG report: 7 in one hour (median gap 4.6 min, max 27 min); SOL 3, ARB 2, LINK 1, AAVE 1, UNI 1,
USDT / GMX / PENDLE / tBTC 0 (`reports_freq.py`, 14,400 blocks to 2026-11-19 10:5x UTC).

Sell paths (`config.json`, pools verified by `token0()/token1()/factory()`): USDG -> USDC on the Slipstream pool
`0x09328BE7...` (fee 0.001 pct, 1.5M USD) -> WETH on Uniswap V3 `0xC6962004...`; the others one Uniswap V3 pool against
WETH, taken from the factory's `getPool` (the fee tier holding the most WETH).

Reports copied from keeper txs are accepted by the FeeHandler's oracle when passed with its provider `0xF4122dF7...`
(`lifttest.py`: `NoProfit(0)` at block 525,596,140; with the keeper's provider `0x204cc947...` the oracle reverts
`0x68b49e6c(given, expected)`). Parsed keeper txs: calls whose arguments hold the price tuple directly
(`executeOrder` 0x7ebc83f7) and `multicall(bytes[])` 0xac9650d8 batches of them (each inner call parsed, newest report
per token kept). The gasless-relay calls 0x8c379335 carry no report bytes and yield nothing. The bot tries the 4 newest
fee-token txs and the 16 newest WETH txs (of 16 WETH txs sampled at block 525,618,929, 4 were executeOrder, 5 multicall,
7 gasless). The oracle also wants the two reports within 60 s of each other (0xdd9c6b9a); the bot's 20 s age limit on
both implies it.

## Read cost

Idle about 32,500 CU/day; a near pot (within 10 pct) adds about 37,000 CU/day (re-read every 180 s); armed about 1,050 CU/min for at most 15 min per token per 2 h; code cap 90,000 CU/day
(0.048 USD/day at 0.53 USD per million CU).

## Proof status (2026-11-19, run 7b88063f)

- Fork success at the paid historical entry (`proof.py`, `proof-result.json`): reset to 525,321,630, the parent of the
  capture `0xd2a01736...`; deploy; NotOwner `0xad9e8535...`; guard NoProfit(4511663393612052) `0x90a86624...`; success
  `0xaafa89d6...` block 525,321,634, owner +0.004424 ETH net of gas (2,910,796 gas); second batch `0x9dea9ba5...`
  +0.004257 ETH; the same call 117 s later reverts in the oracle (`0xd3c82d8e...`, gas only).
- After the success the executor holds no native, WETH, USDC or USDG and has no allowance for any of the three to the
  FeeHandler, the vault or the two pools. The executor itself reverts `Leftover(token)` if a hop leaves input behind
  or the FeeHandler allowance is not back to 0.
- Lost attempt at head (`proof_head.py`, earlier executor): about 4.6M gas, 0.25 USD at 0.03 gwei, 0.17 USD at 0.02 gwei.
