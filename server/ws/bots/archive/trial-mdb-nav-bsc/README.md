trial: MDB+ mint / redeem at its BUSD backing value against the PancakeSwap V2 ESHARE / MDB+ pair on BSC (decision 2026-11-17-cheap-chain-trials)

## What it does

- MDB+ `0x9f8bb16f49393eea4331a39b69071759e54e16ea` (verified on Sourcify, `MDBPlus.sol`) holds BUSD as backing.
  `sell(amount)` burns the caller's MDB+ and pays `backing / totalSupply` per token; `mintWithBacking(busd, to)` mints
  at the same value. Both are open to anyone, no allowlist. At placement (head 135,217,546): price 1.264642 BUSD,
  supply 32,116 MDB+, backing 40,615 BUSD, and `mintFee` = `sellFee` = `transferFee` = 100000 (0 pct; the owner can
  set each up to 3 pct). Every MDB+ call must leave the price not lower (`Price Cannot Fall`).
- Its only pool with takers is PancakeSwap V2 ESHARE / MDB+ `0x51586182a2031f3e384d080f78c8836d48ebbffc` (74.8 MDB+ and
  330.5 ESHARE), and ESHARE trades on WBNB / ESHARE `0x1747af98ebf0b22d500014c7dd52985d736337d2` (11.24 WBNB). The pool
  prices MDB+ in BNB, the backing is BUSD, so the pool drifts away from the backing value when BNB moves against BUSD.
- One transaction through the executor (StepArb), funded by a free WBNB flash loan from Lista Moolah
  `0x8f73b65b4caaf64fba2af91cc5d4a2a1318e5d8c`, all swaps through the PancakeSwap V2 router
  `0x10ed43c718714eb63d5aa57b78b54704e256024e`:
  - redeem (pool below backing): WBNB -> ESHARE -> MDB+, `sell`, BUSD -> WBNB, repay, the rest to the wallet as BNB;
  - mint (pool above backing): WBNB -> BUSD, `mintWithBacking`, MDB+ -> ESHARE -> WBNB, repay, the rest as BNB.
- The executor reverts unless the WBNB left after repayment is at least `minProfit`; the bot sets `minProfit` = that
  send's gas cap. No principal.

## Competition, last 7 days (scratch/r63f9/takes.py 1400000, takes.json)

Every `Redeemed` log of MDB+ in bsc blocks 133,817,402-135,217,402 (10 logs) and every `Minted` log from block
133,890,048 (3 logs):

| time (UTC, block timestamp) | block | tx index | entry (tx.to) | WBNB in | gross BNB | gas BNB |
|---|---|---|---|---|---|---|
| 11-20 18:47:49 | 134,745,810 | 20 | `0xa8619d07` | 0.006773 | 0.000587 | 0.000037 |
| 11-20 18:47:52 | 134,745,815 | 99 | `0xa8619d07` | 0.006773 | 0.000479 | 0.000037 |
| 11-20 18:47:53 | 134,745,819 | 25 | `0xa8619d07` | 0.006773 | 0.000430 | 0.000037 |
| 11-21 03:57:17 | 134,819,057 | 57 | `0xa8619d07` | 0.006334 | 0.000537 | 0.000037 |
| 11-21 03:58:20 | 134,819,197 | 3 | `0xc777a99e` (sender = to) | 0.009037 | 0.000483 | 0.000021 |
| 11-21 03:58:21 | 134,819,199 | 17 | `0xffa26223` | 0.009037 | 0.000302 | 0.000025 |
| 11-21 03:58:21 | 134,819,200 | 6 | `0x0799d396` | 0.009037 | 0.000226 | 0.000026 |
| 11-21 03:58:23 | 134,819,204 | 7 | `0x00000000...` | 0.009037 | 0.000052 | 0.000023 |
| 11-21 04:03:09 | 134,819,839 | 15 | `0x0cffe61d` (sender = to) | 0.002410 | 0.000036 | 0.000021 |

- Nine atomic buy-and-redeem takes, six entry addresses (`0xa8619d07` is driven by rotating `0x888...` senders; it and
  the two self-calling senders route through the helper `0x4813fd4a`), 0.00313 BNB gross in total (1.75 USD at 560
  BUSD per BNB). Priority-fee level: none, all at 0.050-0.0501 gwei (the floor).
- The tenth `Redeemed` (2026-11-17 09:30:13, block 134,095,800) is a 10.4M-gas contract creation that builds a pair
  of a FAKE token with MDB+, mints and redeems 17.8 MDB+: not understood, not copied.
- Mint direction: no take. The three `Minted` logs are two inside that 11-17 transaction and one 0.0098 MDB+ mint by
  the EOA `0xf62b10b2` on 2026-11-22 (block 135,045,144), a plain call with no swap.

## Blocks to take

The takers wait. The bot's own `probe` at past blocks (relay `eth_call` with the code override,
`scratch/trial-mdb-nav-bsc/selftest.py <block>...`), best redeem gain:

| block | relative to the first take of the episode | gain BNB |
|---|---|---|
| 134,735,809 | 10,001 blocks (75 min) before the 11-20 take | 0.000543 |
| 134,744,809 | 1,001 blocks before | 0.000538 |
| 134,745,809 | parent of the first 11-20 take | 0.000644 |
| 134,809,056 | 10,001 blocks before the 11-21 take | 0.000286 |
| 134,818,056 | 1,001 blocks before | 0.000577 |
| 134,819,056 | parent of the first 11-21 take | 0.000608 |
| 134,819,196 | 63 s after it, parent of the second | 0.000481 |
| 134,819,205 | after the fifth | 0.000040 |
| 134,819,838 | 4.8 min later, parent of the last | 0.000035 |

The gain stood above 0.00028 BNB for more than 75 minutes before anyone sent, and the takers came at about 0.0006.
The bot sends above 1.3 x its gas cap (about 0.00005 BNB), so it is earlier by hours, not by blocks. Mint direction at
head: 0.0000106 BNB at block 135,018,219, 0.0000866 at 135,118,219, 0.000106 at 135,218,478 (placement), untaken.

## Loss bound

- `StepArb.take()` reverts `NoProfit` unless the WBNB gained is at least `minProfit`; the bot signs with `minProfit` =
  gas limit x gas price. A lost send costs gas only: about 0.00003 BNB (0.02 USD) at the floor, never above 0.95 USD
  (0.6 gwei x 1.5M gas at a reference price of 1500 USD per BNB).
- It sends only when the best size pays more than 1.3 x that send's gas cap, bids at most 1/3 of gross as gas price,
  and after a lost send waits 5 minutes in that direction.

## Proof

`scratch/trial-mdb-nav-bsc/proof.py` (reset to 134,819,196, the parent of incumbent take `0x94ea967a...`): success
`0x9b027c5d2938f3dcdaeef7538f4277389c94e82a0f33062ca763c0b9b3a66f26` paid the owner 0.000481140 BNB for 474,288 gas
(the incumbent kept 0.000483); reverts for a non-owner, for a `minProfit` it cannot meet, and for a repeat that asks
for the first gain again. `proof.py proof-result-mint.json 135218219` proves the mint direction the same way: success
`0x60c9c5c65b9e4665e8559083911129eeda082e06896ef1027bb60081ac76d8bc` paid 0.000106245 BNB for 509,601 gas.
`selftest.py` runs the paper path through the relay.

## Reads

- No feed filter: the gap moves with the BNB / BUSD price, and neither ESHARE pair had a swap in the 24 h before
  placement, so there is no quiet event to wait on. Timer: one `eth_call` (`probe`, 2 directions x 8 sizes) every 60 s
  = 1,440 x 26 CU = 37,440 CU a day. A standing gain is looked at in full (`eth_gasPrice`, `eth_estimateGas`, one
  `eth_call`, 56 CU) once per 10 minutes or when it grows 10 pct: at most about 8,000 CU a day.
- About 46,000 CU a day = 0.024 USD a day at 0.53 USD per 1M CU. Cap in code 95,000 (then it sleeps to 00:00 UTC).

## Logs (`logs/bot.jsonl`)

`start` (with `executor=`), `opportunity`, `opportunity_skip`, `simulate_revert`, `paper_sim`, `send_result`
(`result` won / lost / unknown, `gas_used`, `winner_block`, `tx_index`), `look`, `heartbeat`, `read_budget`,
`loop_error`.
