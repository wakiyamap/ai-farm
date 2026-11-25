trial: Solv xSolvBTC instant withdraw against the PancakeSwap V3 xSolvBTC / SolvBTC pool on BSC (decision 2026-11-17-cheap-chain-trials)

## What it does

- Solv's `XSolvBTCPool` `0xf50860533d209e44dbe02f58b77ea85a8bfc28a3` (proxy, implementation
  `0xa2a8d11576925feb33262e7d3b3feee7d95cd8ea`, verified on Sourcify) has a public `withdraw(uint256)`: it burns the
  caller's xSolvBTC `0x1346b618dc92810ec74163e4c27004c921d446a5` and mints SolvBTC
  `0x4aae823a6a0b376de6a78e74ecc5b079d38cbcf7` at `getValueByShares` (1.0 now) less a 0.05 pct fee, in the same call.
  No allowlist on `withdraw` (`deposit` is `onlyAllowedCaller`, so the class runs one way only). The admin can change
  the fee.
- xSolvBTC trades on PancakeSwap V3 xSolvBTC / SolvBTC `0x5a5ca75147550079411f6f543b729a4beab4dfeb` (fee 0.05 pct, a
  thin pool: about 0.023 xSolvBTC and 0.010 SolvBTC in it). When a holder sells into the pool instead of withdrawing,
  the pool price drops below the share value. One transaction through the executor then: flash swap on that pool (sell
  SolvBTC, xSolvBTC arrives first), `withdraw`, repay the pool from the withdrawal, sell the SolvBTC left on
  SolvBTC / BTCB `0x12197d7a4fe2d67f9f97ae64d82a44c24b7ad407`, BTCB on BTCB / WBNB
  `0x62edaf2a56c9fb55be5f9b1399ac067f6a37013b`, unwrap, pay the wallet in BNB.
- The executor reverts unless the wallet is paid at least `minProfit`; the bot sets `minProfit` = that send's gas cap.
  No principal: the flash swap funds it.

## Competition, last 7 days

Every `Withdraw` log of the redeemer in bsc blocks 133,803,033-135,147,033 (`scratch/ref08/evscan.py`) and every
`Swap` of the pool (`scratch/trial-xsolvbtc-redeem-bsc/poolstats.py`, `pool-swaps-7d.json`): 17 withdrawals, 5 by users,
12 atomic buy-and-withdraw takes.

| entry contract | takes | senders | lot | median net to sender | max net | tx index |
|---|---|---|---|---|---|---|
| `0x3ee0a37fc6f3857acb155449b632e6776712caea` | 12 | rotating `0x7778...777` keys | 0.0016 BTC (5 of 0.00016) | 0.00016 BNB | 0.0013 BNB | 4-128, median 16 |

- Sender net 0.00436 BNB (2.4 USD at 556 USD per BNB) in 7 days. Nobody else takes.
- Priority-fee level: none, all at 0.0501 gwei (the floor). The incumbent sends about 18 pct of its gain to the builder
  address `0x4848489f0b2bedd788c696e2d79b6b69d7484848` inside the transaction instead of bidding gas.
- Its route: Lista Moolah flash loan of BTCB, BTCB to SolvBTC, SolvBTC to xSolvBTC, `withdraw`, SolvBTC to BTCB. Two
  swap fees more than this bot's route, and fixed small lots.

## Blocks to take

| episode | seller's swap | first take | later takes |
|---|---|---|---|
| 2026-11-21T04:06:13Z | block 134,820,249, 0.009787 xSolvBTC | block 134,820,261: 12 blocks, 5.4 s | 10 more to block 134,820,560 (140 s) |
| 2026-11-22T19:46Z | block 135,137,424, 0.00198 xSolvBTC | block 135,137,431: 7 blocks, 3.2 s | none |

The bot's own `probe()` at past blocks (`series.py`, archive `eth_call` with the code override): 0.00779 BNB from the
seller's block until the first take; 0.0058 BNB after it; 0.0033 BNB 9 s later; 0.0022 BNB 68 s later; 0.0002 BNB at the
end. The ten other sells of the week were 0.00001-0.0002 xSolvBTC and drew no take. A gain of 0.00022-0.00038 BNB has
stood at every sampled block of the 7 days (17 samples) and stands at head 135,147,763 (0.0002995 BNB at 0.00378
SolvBTC): the incumbent's line is above it.

## Loss bound

- `ShareRedeemArb.run()` reverts `NoProfit` unless the BNB paid to the wallet is at least `minProfit`; the bot signs
  with `minProfit` = gas limit x gas price. A lost send costs gas only: about 0.00003 BNB (0.02 USD) at the floor,
  never above 0.95 USD (0.6 gwei x 1.5M gas at a reference price of 1500 USD per BNB).
- It sends only when the best size pays more than 1.3 x that send's gas cap, and bids at most 1/3 of gross as gas price.

## Proof

`scratch/trial-xsolvbtc-redeem-bsc/proof.py` (fork reset to 134,820,260, the parent of incumbent take `0x52f23820...`):
success `0xbf34c74ada97b4728a3bd70c097f5a315bfab3c94e36f94a25b9d46e21383f59` paid the owner 0.007788981 BNB (4.33 USD)
for 653,642 gas (the incumbent's first lot kept 0.0013 BNB); reverts for a non-owner, for a `minProfit` it cannot
meet, and for a repeat after the gap closed.

## Reads

- Feed: one filter, `/logs/bsc` address `0x5a5ca75147550079411f6f543b729a4beab4dfeb`, topic0 PancakeV3 `Swap`
  `0x19b47279...` (24 logs in 7 days). Re-read on `gap`, 429, 503 and connection errors; safety poll every 120 s.
- Relay: one `eth_call` (`probe`, 13 sizes) per look: 720 safety looks + a few feed looks and follow-ups a day
  = about 730 x 26 CU = 19,000 CU; an opportunity adds `eth_gasPrice`, `eth_estimateGas` and one `eth_call`
  (56 CU). About 20,000 CU a day with the feed's share = 0.011 USD a day at 0.53 USD per 1M CU. Cap in code 95,000.
- Paper: the standing gain is never taken, so every look also runs `eth_gasPrice`, `eth_estimateGas` and the exact
  call: 720 x 82 CU = 59,000 CU a day (no follow-up looks in paper). Live: once the gain is taken a look is 26 CU.

## Logs (`logs/bot.jsonl`)

`start` (with `executor=`), `feed`, `opportunity`, `opportunity_skip`, `simulate_revert`, `paper_sim`, `send_result`
(`result` won / lost / unknown, `gas_used`, `winner_block`, `tx_index`), `heartbeat`, `read_budget`, `loop_error`.
