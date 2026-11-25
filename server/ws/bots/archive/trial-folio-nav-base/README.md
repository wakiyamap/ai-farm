trial

# trial-folio-nav-base

Cheap-chain trial (decision 2026-11-17-cheap-chain-trials). Reserve Folio LCAP ("CF Large Cap Index",
0x4da9a0f397db1397902070f93a4d6ddbc0e0e6e8, 3.7M USD) on Base can be redeemed for its basket by anyone with
`Folio.redeem(shares, receiver, assets, minAmountsOut)`. When LCAP is cheap in its Aerodrome Slipstream LCAP/USDC
pool (0xc8c15670..., fee 0.3 pct) relative to the basket (cbBTC, WETH, cbXRP, cbADA, SOL, cbDOGE, HYPE), this round
trip pays, in one transaction through the bot's executor:

flash WETH (Balancer V2 Vault, fee 0) -> USDC (Uniswap V3 0.01 pct) -> LCAP (the pool) -> `redeem` -> sell the six
non-WETH basket tokens for WETH in the pools the incumbent uses -> repay -> the WETH gain is unwrapped and paid to the
bot wallet as native ETH. The executor reverts `NoProfit` unless the gain is at least `minProfit`.

## Honest expectation

The bot will send rarely and win rarely. It exists to measure that by sending.

- Past 7 days (blocks 56,739,092-59,763,092, Transfer from / to 0x0 on the 13 Base Folios,
  `scratch/ic-76eb/folio.py`): 1,806 mint / redeem transactions. LCAP 1,035 (574 mints, 461 redeems), BGCI 417,
  ABX 239, CLX 76, MVTT10F 34.
- Who: executor 0xb52603cef75de7538e42ee764a775d5e707ce528 does 1,539 of them (LCAP 530 mints + 423 redeems, BGCI
  413, ABX 173), driven by EOAs 0x4cbf9040, 0x85bc7f30, 0xf911032a, 0xe253103e, 0xbe77d0c6, 0x4701dc9a (entry selector
  0xa9059cbb on the executor). Others: 0x7b03b0fa (LCAP, 47, sender 0xd2c2673a), 0x90bfa62b (CLX mints, 40, vanity
  0xc0ffee... senders), 0xf7c70a04 (35, sender 0x3de7e4a0), 0x3e0aafe2 (CLX redeems, 23).
- What a take pays (154 sampled takes of 0xb52603ce, `scratch/ic-76eb/folio_gain.py`): gross median 0.043 USD, p90
  0.115, max 3.69 (USDC to the sender plus WETH kept in the executor, ETH at 1,810); gas median 0.031 USD
  (1.58M gas at about 0.011 gwei); net median 0.012 USD, 20 pct of takes net negative. Whole class: about 13 USD a
  day net for the incumbent.
- Priority fee of the incumbent on 42 sampled LCAP redeems: 0.0054-0.0159 gwei, median 0.0061 (about the base fee
  again); tx index 4-195, median 38 (not a first-in-block job).
- Blocks to take (`scratch/trial-folio-nav-base/series.py`, `series-windows.json`): this bot's own route, probed at
  0.02 WETH with a code override at blocks before each of the 42 incumbent LCAP redeems. A gain was visible at the
  parent block for 16 of 42 (above 1e13 wei, about one gas cap, for 5), 1 s before (5 blocks) for 11 (3), 3 s before
  (15 blocks) for 5 (0), 10 s before for 4 (0), 30 s before for 2 (0), 90 s before for 0. For 26 of 42 the farm route
  shows nothing even one block earlier: the incumbent takes inside the block in which the gap opens, at a lower
  break-even than this route.
- So: gaps above the bot's gas cap stood 0.2-1 s. With a 3 s reaction the bot expects to see such a state a few
  times a week and to lose most sends to the incumbent. Paid entries in the last 7 days whose gross exceeds one
  attempt's gas: yes (e.g. 0x895704c4..., block 59,118,274, 0.109 USDC to the sender).

## What it does

- Every 30 s, and on every Swap of the LCAP/USDC pool (feed `/logs/base`, address 0xc8c15670050541255f9b797c008047682524861f,
  topic0 0xc42079f9... Swap; about 150-200 logs a day), one `eth_call` of the executor's `probe()` at 0.02 WETH.
  On feed `gap`, HTTP 429 / 503 or a timeout the timer keeps re-reading state.
- A gain: sweep 0.01 / 0.02 / 0.04 / 0.06 / 0.08 WETH, estimate gas, gas limit = estimate x 1.2 + 100,000, tip = at most
  20 pct of gross, cap = gasLimit x maxFeePerGas + L1 allowance. Send only if the simulated gross is above the cap,
  with `minProfit = cap + 1`, after simulating the exact call at the signed gas limit.
- Paper mode logs `paper_sim`; live mode sends through the signer and logs `send` and `send_result` (won / lost, gas
  used, the winner's block and tx = last LCAP/USDC pool swap up to our block).

## Limits

- Base (OP Stack): the enforceable worst case of a send is the wallet's native balance. The manifest funds 0.75 USD
  and the bot refuses to sign while the balance is worth 0.95 USD or more (`wallet_bound`, bot.py:236).
- Signed gas cap of a send: about 2.3M gas x 0.0066 gwei = 1.5e13-1.8e13 wei = 0.03 USD.
- No principal: the WETH is flash-borrowed inside the transaction.

## Read cost

Timer 2,880 probes x 26 CU = 74,880 CU a day; feed-triggered probes about 200 x 26 = 5,200; sweeps about 200 CU
each. About 81,000 relay CU a day = 0.043 USD at 0.53 USD per million; code cap 93,000. Feed: one filter, under
2,000 CU a day.

## Fork proof and self-test

`python3 scratch/trial-folio-nav-base/proof.py 59118273 proof-result-59118273.json` (one Base fork lease: reset to
the parent of the incumbent take 0x895704c4..., deploy, fund, non-owner, guard, success, repeat). Results in the
manifest. `scratch/trial-folio-nav-base/selftest.py <block>...` checks the hand ABI encodings against cast and
replays the bot's own `check()` at past blocks.

## Not built

- The mint direction (buy the basket, `mint`, sell LCAP): 574 of the 1,035 LCAP takes. Needs exact-output swaps in
  basket proportion and the mint fee; the executor has no such step.
- BGCI (its route has a V2 pair) and ABX (a Uniswap V4 pool): the executor swaps UniV3-style pools only.
