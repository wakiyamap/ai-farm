trial: Cakepie CKP fixed-rate compensation against the PancakeSwap V3 CKP pool on BSC (decision 2026-11-17-cheap-chain-trials)

## What it does

- The Cakepie compensation contract `0x7ae3f2672486ada489e41e8a23bba414ee7db4c7` (ERC-1967 proxy, implementation
  `0x020217c298bb8a492f4863d3296f952fac920bed`) pays `usdtCmpPerCkp()` = 0.5199 USDT for every CKP
  `0x2b5d9adea07b590b638ffc165792b2c610eda649` burnt through it: `compensate(amount)` pulls and burns the caller's CKP,
  `claim()` pays the USDT. Open to anyone, no allowlist, no snapshot; 2,594,844 CKP compensated so far, 162,144 USDT
  left in it (head 135,115,111). The owner can pause it, change the rate and recover tokens.
- CKP trades on PancakeSwap V3 CKP / WBNB `0x8b626acfb32cdad0d2f3b493eb9928bba1bbbcca` (fee 0.25 pct). When a holder
  sells into the pool, or BNB falls against USDT, the pool price drops below the rate less fees. One transaction
  through the executor then: flash swap on PancakeSwap V3 USDT / WBNB `0x172fcd41e0913e95784454622d1c3724f546f849`
  (sell USDT, WBNB arrives first), WBNB to CKP on the CKP pool, `compensate`, `claim`, repay the USDT pool from the
  claim, sell the USDT left for WBNB, unwrap, pay the wallet in BNB.
- The executor reverts unless the wallet is paid at least `minProfit`; the bot sets `minProfit` = that send's gas cap.
  No principal: the flash swap funds it.

## Competition, last 7 days (scratch/trial-ckp-comp-bsc/census.py 1344000, census-7d.txt, stats.py)

Every log of the compensation contract in bsc blocks 133,771,296-135,115,296 (from 2026-11-15T16:55:51Z, block
timestamps): 37 takes, all atomic buy-and-compensate transactions, 10,781 CKP for 5,605 USDT, rate 0.5199 in every one.

| entry contract | takes | senders | median flash | median net to sender | max net | median tx index |
|---|---|---|---|---|---|---|
| `0x3ee0a37fc6f3857acb155449b632e6776712caea` | 17 | 12 rotating keys | 100 USDT | 0.00009 BNB | 0.00126 BNB | 22 |
| `0xf38c67a72476b23e60700dc0bbad07d7be02ea14` | 9 | 9 | 63 USDT | 0.00026 BNB | 0.0198 BNB | 45 |
| `0x0000000000be226afde21672a5e4adc45692e69d` | 5 | 5 | 36 USDT | paid elsewhere | - | 16 |
| `0x3842664d3699d1a17d86e9f60beea724565ee1bb` | 3 | 3 | 1,003 USDT | 0.0032 BNB | 0.1155 BNB | 3 |
| `0xffa26223e5facdc822fcc7f82cc6297e83042b8a` | 2 | 2 | 59 USDT | 0.0002 BNB | 0.00026 BNB | 7 |
| `0x81ee41c232e2c7fba40c9eac02ae1eae33570382` | 1 | 1 | 189 USDT | negative | - | 69 |

- Net to the senders 0.148 BNB (83 USD at 560 USD per BNB), 0.1155 BNB of it in one take on 2026-11-16T01:51:14Z, one
  block after a 2,099 CKP dump. Median positive take 0.000128 BNB (0.07 USD); gas 0.00004 BNB (0.022 USD).
- Priority-fee level: none. All 37 at 0.05-0.068 gwei (the floor). `0xf38c67a7` sends 25 pct of its gain to the
  builder address `0x4848489f0b2bedd788c696e2d79b6b69d7484848` inside the transaction instead of bidding gas.
- Episodes: 2026-11-16T01:51Z (4 takes), 2026-11-16T16:14:38Z (1), 2026-11-20T15:16:29Z to 2026-11-21T04:07:27Z (32).
  None in the 37 h before placement.

## Blocks to take (windows.py, windows.json)

The 32 takes of 11-20 / 11-21 against the newest CKP sell on the pool by anyone else (0.45 s blocks):

| distance | takes |
|---|---|
| same block | 3 |
| 1-7 blocks (within 3 s) | 8 |
| later | 21 |

Median 140 blocks (63 s), minimum 0. The late ones follow BNB / USDT moves, not a swap on the CKP pool, which is why
the bot also looks every 120 s. The 3,486 CKP dump of 2026-11-22T15:28:59Z (block 135,103,175) was bought back inside
the same block through other pools and nobody compensated: the large ones are gone before a public sender can act.

## Loss bound

- `CompensationArb.run()` reverts `NoProfit` unless the BNB paid to the wallet is at least `minProfit`; the bot signs
  with `minProfit` = gas limit x gas price. A lost send costs gas only: about 0.00003 BNB (0.02 USD) at the floor,
  never above 0.95 USD (0.6 gwei x 1.5M gas at a reference price of 1500 USD per BNB).
- It sends only when the best size pays more than 1.3 x that send's gas cap, and bids at most 1/3 of gross as gas price.

## Proof

`scratch/trial-ckp-comp-bsc/proof.py` (fork reset to 134,815,626, the parent of incumbent take `0xacb524e5...`):
success `0x1c6c6b204cc6ef56089816e90ed9f82d2944e4b72172765e8f3fba8c88528c03` paid the owner 0.000302494 BNB for
449,973 gas (the incumbent kept 0.000175 BNB after its builder tip); reverts for a non-owner, for a `minProfit` it
cannot meet, and for a repeat after the gap closed. `selftest.py` runs the paper path through the relay.

## Reads

- Feed: one filter, `/logs/bsc` address `0x8b626acfb32cdad0d2f3b493eb9928bba1bbbcca`, topic0 PancakeV3 `Swap`
  `0x19b47279...` (about 90 logs a day). Re-read on `gap`, 429, 503 and connection errors; safety poll every 120 s.
- Relay: one `eth_call` (`probe`, 13 sizes) per look: 720 safety looks + about 90 feed looks + follow-ups a day
  = about 900 x 26 CU = 23,400 CU; an opportunity adds `eth_gasPrice`, `eth_estimateGas` and one `eth_call`
  (56 CU). About 28,000 CU a day with the feed's share = 0.015 USD a day at 0.53 USD per 1M CU. Cap in code 95,000.

## Logs (`logs/bot.jsonl`)

`start` (with `executor=`), `feed`, `opportunity`, `opportunity_skip`, `simulate_revert`, `paper_sim`, `send_result`
(`result` won / lost / unknown, `gas_used`, `winner_block`, `tx_index`), `heartbeat`, `read_budget`, `loop_error`.
