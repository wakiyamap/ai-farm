trial

# trial-torex-base

Trial bot (decision 2026-11-17-cheap-chain-trials): a liquidity mover for SuperBoring Torex pools on Base.

## Mechanism

A Torex collects a Superfluid stream of an in super token (a DCA order book). Anyone may call
`Torex.moveLiquidity(bytes)`: the Torex sends its whole accumulated in-token balance to the caller and, in
`moveLiquidityCallback`, asks for `minOut = TWAP since the last move x fv / (fv + t)` of the out super token.
The discount grows with the time `t` since the last move (about 0.28 pct per 1000 s on these pools), so the
first mover whose costs are covered takes it; the mover keeps what the swap pays above `minOut`.
Source: verified Torex at `0x269f9ef6868f70fb20ddf7cfdf69fe1dbfd307de` (`src/Torex.sol`, `src/TorexCore.sol`,
`src/libs/DiscountFactor.sol`); no caller gate (fork: the farm executor's moves succeed).

The executor `TorexMover` does it in one transaction: receive the in super token, unwrap it, swap on
Uniswap V3 SwapRouter02 along a path given as an argument, wrap exactly `minOut`, pay the Torex, pay the rest
to the owner as native ETH or USDC, revert `NoProfit` unless that rest is at least `minProfit` (> 0).

## Routes (all arguments, none baked into the contract)

| route | Torex | swap |
|---|---|---|
| USDCx-ETHx | 0x269f9ef6868f70fb20ddf7cfdf69fe1dbfd307de | USDC -0.01- WETH, profit ETH |
| SUP-ETHx | 0x3f9e46eb52c124067e6bee4913601419d4b1d4b9 | SUP -0.3- WETH, profit ETH |
| USDCx-SUP | 0xc3b4f5177e3d706931789b159e1df433c20439f1 | exactOutput USDC -0.01- WETH -0.3- SUP, profit USDC |
| ETHx-USDCx | 0x267264cfb67b015ea23c97c07d609fbfc06adc17 | WETH -0.01- USDC, profit USDC |
| SUP-USDCx | 0x91c673f8ab9dbfd95847f6c7e62fa4a72110337e | SUP -0.3- WETH -0.01- USDC, profit USDC |

## Competition, last 7 days (blocks 57,323,179-60,327,105, scan to head 60,339,330 at 2026-11-21 10:5xZ)

Topic-only `eth_getLogs` of `LiquidityMoved` (topic0 `0xc8333a73...608a`, read from a receipt), 0 error pages:
1,270 moves on 33 Torexes, two mover contracts only:

- `0x1e77916e3fed4a24dc4e37968587e2b71d3a9c06`: 968 moves; driven by EOA `0x04a1f49b...` through the automation
  contract `0x1432960c...`; 2.65-2.78M gas per move at 0.007 gwei (base fee 0.005 + tip 0.002 gwei), tx index 4-50.
- `0x8b249337369f4190582c152c5b5910b97a4525bf`: 302 moves.

Only the five Torexes above carry value (about 170 USD of volume a day together); the other 28 hold dust and
are moved every 6 h. Per route (moves, seconds from the previous move to the take min / median / max,
discount at the take min / median / max; `scratch/trial-torex-base/week.py`):

| route | moves 7 d | seconds to take | discount pct at take |
|---|---|---|---|
| USDCx-ETHx | 112 | 843 / 5437 / 9888 | 0.24 / 1.50 / 2.70 |
| SUP-ETHx | 108 | 2771 / 5444 / 9273 | 0.77 / 1.50 / 2.54 |
| USDCx-SUP | 122 | 1848 / 5213 / 11323 | 0.52 / 1.44 / 3.08 |
| ETHx-USDCx | 90 | 15 / 7023 / 13491 | 0.00 / 1.93 / 3.65 |
| SUP-USDCx | 67 | 2636 / 8986 / 16442 | 0.73 / 2.46 / 4.41 |

A take is worth 0.02-0.045 USD gross (traced: 2.89 USDC in, mover kept 0.0000265 ETH = 0.043 USD, gas
0.03 USD, tx `0x0a733e7a...1ac1`). This is a threshold contest, not a same-block race: blocks to take are
thousands (a Torex sits takeable-at-a-smaller-profit for many minutes). The bot's edge is gas: 1.93-2.06M
(fork) against the incumbent's 2.65M+, so its break-even comes a few minutes earlier. Share aimed at: the
rounds where gross passes the bot's gas cap before the incumbents' threshold; honest expectation
0.1-0.5 USD a day net. At the head on 2026-11-21 10:50Z two routes simulated above the cap
(`scratch/trial-torex-base/selftest.py`, and the first `paper_sim` lines of the paper log).

## Send rule and loss bound

- Timer: every 120 s per Torex (300 s for the two small ones) once 1500 s have passed since its last move;
  one `eth_call` of the executor per look.
- Send only when simulated gross (in wei) > `gasLimit x maxFee + 1.2 x L1 fee` (gasLimit = estimate x 1.1,
  maxFee = base fee x 1.1 + tip); tip = at most 10 pct of gross, capped at 0.003 gwei.
- `minProfit` = half the simulated gross; the executor reverts below it, so a lost attempt costs gas only:
  0.85-2.2M gas for a revert on an emptied Torex (fork) = under 0.02 USD at 0.005 gwei. Hard bounds: 2.5M gas,
  0.06 gwei, 0.95 USD a send at 6000 USD per ETH.
- Log line per send: `send_result` with won / lost, gas used, send block, winner block and winner mover.

## Read cost

Paper and live alike: about 2,400 looks a day x 26 CU = 62k CU, plus resyncs and the 4 extra calls of an
opportunity: about 70k CU a day = 0.04 USD a day at 0.53 USD per 1M CU. The bot stops reading at 95k CU a day
(every read, startup included, is inside the handler that sleeps to 00:00 UTC).

## Fork proof

`python3 scratch/trial-torex-base/proof.py` (reset 60,315,659) and `proof.py 60313822` (the exactOutput
route); hashes and deltas in the manifest and `proof-result-*.json`. Paper mode simulates with the fork
deployment's runtime code (`executor-runtime.hex`, owner `0x1111...1111`) as a state override.

## After the trial

After 7 days live or when the 10 USD is spent: an `attempts` row with sends / wins / net and how many blocks
before the bot's send the winner landed; lead to `measured` or `blocked_infra`.
