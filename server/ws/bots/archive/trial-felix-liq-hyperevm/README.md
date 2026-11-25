# trial: trial-felix-liq-hyperevm

**Trial bot** (decision 2026-11-17-cheap-chain-trials): cheap chain, race rule and EV floor waived, the
win rate is measured live by sending. Built from lead 278 (run 35944637, 2026-11-18).

Felix feUSD CDP on HyperEVM is a Liquity V2 fork. `TroveManager.batchLiquidateTroves(uint256[])` is
public (verified source, implementation 0x473c5e001615e64a24d6c961ba1ab2642e797f2e, no role). For every
listed trove whose ICR is under the branch MCR it closes the trove against the Stability Pool and sends
**0.5 % of the trove's collateral to the caller** (`collGasCompensation = entireColl / 200`; Liquity's
2-unit cap is not applied in this fork, `ETH_GAS_COMPENSATION` is 0). The caller needs no principal.

The executor `FelixLiqTake.take(troveManager, troveIds, collateral, wnative, pool, minProfit)` calls it,
sells a non-WHYPE reward for WHYPE on the UniV3-style pool given as argument, unwraps WHYPE, reverts
`NoProfit` unless its native balance grew by `minProfit`, and pays the bot wallet in native HYPE.

Branches covered: WHYPE (TroveManager 0x3100f4e7bda2ed2452d9a57eb30260ab071bbe62, 58 troves, MCR 135 %)
and kHYPE (0x7c07bb77b1cf9a5b40d92f805c10d90c90957e4a, 19 troves, MCR 135 %, reward sold on the
kHYPE/WHYPE pool 0xbe352daf66af94ccf2012a154a67daef95facb91). UBTC (0xbbe5f227..., 23 troves) is not
covered: no route to native is proven for it.

## Competition, last 7 days (to block 51,609,477; `scratch/trial-felix-liq/scan.py`, `windows.py`)

All logs of the three TroveManagers: 3 `Liquidation` events (topic0 0x7243af9a...), 4 troves, all on
2026-11-14 (the HYPE drop), three different takers:

| tx | block | branch | reward to caller | taker | tx index | priority fee | gas cost | takeable before the take |
|---|---|---|---|---|---|---|---|---|
| 0x441676e4..aebfc | 51,273,226 | kHYPE | 31.813 kHYPE (2,059 USD) | EOA 0xd81217f8 via contract 0x8b363fcb | 0 of 18 | 3,459 gwei | 2.39 HYPE | 1 block (not 2) |
| 0xb804f1fd..658e | 51,274,476 | WHYPE, 2 troves | 12.239 WHYPE (757 USD) | EOA 0xd9fffdf0, direct call | 0 of 24 | 4,319 gwei | 2.91 HYPE | 2 blocks (not 3) |
| 0x7ebec39e..7fb3 | 51,274,511 | WHYPE | 0.2435 WHYPE (15 USD) | EOA 0x3e8a805d, direct call | 6 of 21 | 230 gwei | 0.149 HYPE | 5-9 blocks |

- Blocks to take: 1, 2 and 5-9 (about 1 s each). "Takeable" = a stranger's `eth_call` of the same
  `batchLiquidateTroves` succeeds at that earlier block.
- Priority-fee level: 230-4,319 gwei, i.e. 7-60 % of the reward; base fee 2.8-49 gwei in those blocks
  (0.1 gwei on a quiet day).
- This bot's cap is 1 USD per send: about 12-17 gwei at these gas limits. It cannot outbid those takers
  inside a block. It wins only by landing a block earlier (4 s poll while a trove is within 1.5 % of
  MCR) and only while the base fee is under its ceiling (the 15 USD lot at 49 gwei would be skipped).
  A lost attempt reverts `NothingToLiquidate` at about 137k gas: 0.002 HYPE (0.14 USD) at 15 gwei.

## Fork proof

`scratch/trial-felix-liq/proof.py` (one script, head fork because the hyperevm fork serves head storage
at any reset block, `pitfalls/hyperevm-fork-head-state.md`; output `proof-result.json`):

- DEPLOY 0x546ecf4f..ce06 gas 610,581, executor 0x7986a41cf80d6d20f7b96c11f600b7882ab29e2c
- NOTHING-TO-TAKE at head 0x989d5224..c299 status 0 (`NothingToLiquidate` 0x8c20998d)
- a fork-made stranger opens a WHYPE trove: 1,000 feUSD, 20.4496 WHYPE (0.002 % above the lowest
  accepted collateral), interest rate 250 %; HEALTHY guard 0x99f2cc26..8a52 status 0
- `evm_increaseTime 3600`: one hour of interest puts ICR under MCR
- NON-OWNER 0x7a9e6f19..a2c status 0; NO-PROFIT (minProfit 1,000 HYPE) 0x2a3b2dc6..d644 status 0
- SUCCESS 0x0490fef7..7ebf status 1, gas 556,251, block 51,609,847, ids = [a healthy trove, the new
  trove]: **owner native +0.101673409 HYPE** after gas, gross 0.102247970 HYPE = collateral / 200;
  executor native 0, WHYPE 0 afterwards
- REPEAT 0xaf9880fd..3a27 status 0 (`NothingToLiquidate`)

Past cases, `scratch/trial-felix-liq/hist.py` (relay `eth_call` with the fork runtime as code override):
gain 32.669041 HYPE at block 51,273,225 (kHYPE route), 12.238861 HYPE at 51,274,475 and 51,274,474,
0.2435 HYPE at 51,274,510 / 509 / 506; `NothingToLiquidate` before each window.

`scratch/trial-felix-liq/selftest.py` runs this bot's own `check()` at those blocks (`python3 bot.py
selftest <block>`): it finds the same troves (ICR 1.3462-1.3497 against MCR 1.35) and logs
`opportunity` with gains 0.2435, 12.238861 and 32.669041 HYPE, gas limits 821k-1.11M, gas cap 0.88 USD;
at the quiet block 51,274,400 and at head it logs only `check` (`selftest.out`).

Paper mode simulates the exact call with `eth_call` and a code override (`executor-runtime.hex`) at the
fork address, from the owner baked into that runtime (0xc0ffee..2378). Live mode uses the signer's
address and `EXECUTOR_ADDR_HYPEREVM` / `EXECUTOR_ADDR`.

## What the bot does

- Start: per branch, price feed address (TroveManager storage slot 2) and MCR (BorrowerOperations).
- Every 30 min: trove id list (`getTroveIdsCount`, `getTroveFromTroveIdsArray`), two Multicall calls.
- Every poll: ONE Multicall3 `eth_call` = `fetchPrice()` of both feeds + `getLatestTroveData(id)` of all
  77 troves; ICR = coll x price / debt. Interval 60 s; 12 s when the nearest trove is within 4 % of MCR;
  4 s within 1.5 %. No price event exists to wait for on the feed (the oracle is read, not pushed), so
  this is a timer.
- Trove under MCR: simulate `take` for up to 2 troves of the branch (largest collateral first), estimate
  gas, log `opportunity`, send in live mode. 45 s cooldown per trove, at most 15 sends per UTC day.

## Send rule and loss bound

Send only when the simulated reward is above that send's gas cap: `gasLimit x maxFeePerGas`, with
`gasLimit = eth_estimateGas x 1.25` (refused above 1,900,000), `maxFeePerGas = min(fee ceiling,
2 x gas price + priority)`, priority = at most 50 % of the reward, and the fee ceiling chosen so the whole
expression stays under 0.90 USD at Felix's own HYPE/USD price. `minProfit` in the call is that cap, so a
mined transaction either nets more than its gas cap or reverts. Worst case per send = gas, under 1 USD.
Every send logs `send_result` with won / lost, gas used, gas cost, the winner's block and tx, and how
many blocks after the winner it landed.

## Reads

Normal state: 1,440 polls x 26 CU + 96 list calls x 26 CU = about 40,000 relay CU/day = 0.021 USD/day at
0.53 USD per 1M CU. Fast polling near MCR costs up to 23k CU/hour, so relay reads stop at 90,000 CU per
UTC day (`RELAY_CU_CAP`); the bot then sleeps 10 min at a time until the next day. No feed subscription.
