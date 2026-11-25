trial

# trial-dfm-pegkeeper-arbitrum

defi.money (stablecoin MONEY `0x69420f9e38a4e60a62224c489be4bf7a94402496`) runs Curve-style PegKeepers on Arbitrum.
Its `PegKeeperRegulator` (`0xf2b12abebf522d4a0f195ac21a6c9af196ed1595`, verified Vyper source) has an unguarded
`update(pk, beneficiary)`: once 30 s (`action_delay`) have passed since the keeper's last action, the keeper provides
or withdraws `min(imbalance / 5, allowed)` MONEY in its Curve StableSwap-NG pool and sends `caller_share` (20 pct) of
the new profit to the beneficiary as pool LP tokens. One transaction through the StepArb executor does:

    Morpho flash 1 USDC (frame only) -> regulator.update(USDT keeper, executor) -> pool.remove_liquidity_one_coin(LP -> USDT)
    -> SwapRouter02 USDT -> USDC -> repay 1 USDC -> the rest to the bot wallet as USDC

and reverts unless the executor's USDC grew by `minProfit`. A lost attempt costs only gas.

Only the USDT keeper is taken (`0x294e6a40...`, pool `0x81fdbd70...`, 238 USDT + 134 MONEY at 13:54Z). The crvUSD
keeper pays a fifth of that (0.003-0.011 LP), the DAI and USDC pools hold 1-4 USD, the FRAX keeper is banned by the
regulator. Adding a keeper is one `ROUTES` line (keeper, pool, coin index, coin, Uniswap V3 fee tier to USDC).

## Competition, last 7 days (blocks 523,835,204-526,255,204; `scratch/trial-dfm-pegkeeper-arbitrum/history.py`)

| block | UTC (2026-11-21) | sender | keepers | USDT keeper share (LP) | all keepers (LP) | gas (wei) | tx index | s since its previous action |
|---|---|---|---|---|---|---|---|---|
| 526,166,654 | 06:50:12 | 0x629dad15 | 2 | 0.0294 | 0.0328 | 1.54e13 | - | (first in 7 d) |
| 526,224,717 | 11:33:55 | 0x629dad15 | 4 | 0.0405 | 0.0495 | 2.34e13 | - | 17,023 |
| 526,250,483 | 13:36:38 | 0x629dad15 | 4 | 0.0448 | 0.0542 | 2.59e13 | - | 7,363 |
| 526,250,784 | 13:37:54 | 0x629dad15 | 4 | 0.0513 | 0.0621 | 2.28e13 | 9 | 76 |
| 526,251,081 | 13:39:09 | 0x629dad15 | 4 | 0.0531 | 0.0642 | 2.42e13 | 29 | 75 |
| 526,251,394 | 13:40:28 | 0x629dad15 | 2 | 0.0229 | 0.0276 | 1.43e13 | 9 | 79 |

One address (EOA `0x629dad154ef836df0acc060aaff2399709440fd4`, through Multicall3, beneficiary `0x344e42e3...`), six
transactions, all on one day; the one before is from 2026-06-15. Priority fee: none (Arbitrum orders by arrival; gas
price 0.02 gwei). Blocks to take: the contract opens the next action 30 s after the last one; the incumbent came 75-79 s
after (about 180 blocks after it opened), and hours after for the first action of an episode. At 13:54:35Z a share of
0.0117 LP had stood untaken for 847 s: the incumbent has a bar, and so does this bot (its gas cap).

A stranger is paid: `eth_call` of `update(pk, stranger)` from a fresh address at block 526,254,626 returned
`caller_profit` 0.011656 LP (USDT keeper) and 0.005287 LP (crvUSD keeper) (`scratch/r8980-pk-state.py`), and the fork
run below moved 0.045868 USDC to the owner.

## Size, honestly

Cents. A won send nets about 0.02 USD (0.046 USDC gross, 735,827 gas = 0.024 USD at 0.02 gwei). Three of the six past
updates were above the bot's send line (gross above the gas cap, about 0.043 USDC). The trial measures whether the farm
wins a keeper reward with a 30 s contract delay against one incumbent that polls slowly; it will not earn more than
a few cents a day, and an episode may not recur before the trials close (11-24).

## Send rule (bot.py `check`)

1. Every 40 s: one `probe()` `eth_call` of the exact `take()` (paper: with the executor code override). Result = USDC
   gained; 0 when it would revert (action delay, regulator ban, peg unprofitable).
2. Below 0.025 USDC (one update costs about 0.024 USD of gas), or below 80 pct of the gas cap computed in the last 10 min: a `check` line, nothing else.
3. Otherwise: base fee, `eth_estimateGas` (Arbitrum: never a constant) x 1.2, `maxFeePerGas` = base fee x 1.25 (refused
   above 0.5 gwei), cap = limit x fee, converted to USDC at the Uniswap V3 WETH/USDC pool price.
4. Send only when gross > cap (and cap < 0.95 USD at 4,000 USD per ETH); `minProfit` = cap in USDC; the signed call
   is re-simulated first. After a live send, three more looks 31 / 62 / 93 s later (the keeper may act again).
5. Every send logs `send_result` with `result` won / lost, `gas_used`, `send_block`, `winner_block`.

## Fork proof

`python3 scratch/trial-dfm-pegkeeper-arbitrum/proof.py` (reset 526,250,482, the parent of the incumbent's 13:36:38Z
update; `proof-result-526250482.json`): probe 0.045868 USDC; stranger probe reverts; non-owner `NotOwner`
0x359bb3d8...; guard `NoProfit(45868, 1e24)` 0x50604d63...; success 0x3279c55d... (fork block 526,250,486, 735,827
gas, owner +0.045868 USDC); the same call in the next block reverts `StepFailed(0, "DFM:R Action delay still active")`
0x5cdb54b5...; executor balances and allowances 0.

## Addresses

| what | address | check |
|---|---|---|
| PegKeeperRegulator | 0xf2b12abebf522d4a0f195ac21a6c9af196ed1595 | verified source (explorer), constructor arg of the PegKeeper, `action_delay()` = 30, `peg_keepers(0..4)` |
| USDT PegKeeper | 0x294e6a40b208c483ef35cdde4f133d042a68390f | `peg_keepers(0)`, verified source `PegKeeper`, `caller_share()` = 20000 |
| its pool / LP | 0x81fdbd700db44c3e57639c2c4518630945c132a6 | `peg_keepers(0).pool`, `coins(0)` = USDT, `coins(1)` = MONEY, `N_COINS()` = 2 |
| USDT (USD₮0) | 0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9 | `pool.coins(0)`, `symbol()` |
| USDC | 0xaf88d065e77c8cC2239327C5EDb3A432268e5831 | token1 of the WETH/USDC pool, the USDC keeper's `coins(0)` |
| SwapRouter02 | 0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45 | `factory()` = 0x1F98431c..., `getPool(USDT, USDC, 100)` = 0xbe3ad6a5... (54,625 USDC + 619,923 USDT) |
| Morpho Blue | 0x6c247b1F6182318877311737BaC0844bAa518F5e | holds 360,425 USDC; same lender as the live trial-ryeth-arb-arbitrum |
| WETH/USDC 0.05 pct | 0xC6962004f452bE9203591991D15f6b388e09E8D0 | `token0()` WETH, `token1()` USDC, `factory()` 0x1F98431c... |

## Read cost

One `eth_call` (26 CU) per 40 s = 2,160 x 26 = 56,160 CU/day with nothing to take; a look that sees a share adds a
block read, an estimate and a guard simulation (86 CU). Code cap 95,000 CU/day, then sleep to 00:00 UTC (every read
is inside the handler). 0.030-0.050 USD/day at 0.53 USD per million CU. No feed filter.
