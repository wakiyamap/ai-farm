trial — public `harvest(token)` of the Lester Labs launchpad migrator on Base, for its caller tip.

## What it does

The launchpad (`Launchpad` 0x23231924281b34bb28f10d854db8d2dcbd7f78c5, 62 coins) taxes trades on a graduated
coin's Uniswap V2 pair in coins. `UniV2Migrator` 0x60070f76f885616d675305624497ed0797303434 has
`harvest(address token)` (selector 0x0e5c011e), open to anyone: once per 5 minutes per coin it sells a slice of the
tax buckets (at most 0.5 % of the pair's quote side) and pays `msg.sender` a twentieth of the treasury's part in the
coin's quote asset (cbLTC for both live coins). The bot simulates its executor's `take()` every 120 s for LESTER and
NOTUS; when the gain is at least 1.5 x the gas cap it sends one transaction: harvest, sell the cbLTC tip to WETH on
the Aerodrome CL pool 0x200681425b0c8d78c6a467512c5d49fa56bac88a, unwrap, pay the wallet. The executor reverts
unless more than the gas cap arrives (`minProfit = cap + 1`).

## Competition, 7 days to 2026-11-22 01:45Z (blocks 57,583,257-60,607,257)

Source: `scratch/r2cb0/measure.py` (`harvests.json`), `scratch/trial-lester-harvest-base/competition.py`
(`competition.json`, last 24 takes), attempts:3550.

| taker | takes | coin | tip median | priority fee | tx index |
|---|---|---|---|---|---|
| executor 0x3c93eb22fed586a83a9578bfa0246653d7258a36 (senders 0xc0ffee..) | 41 | almost only LESTER | 83,849 sat (0.033 USD), min 28,468 | 0.0014-0.0124 gwei | 5-16 |
| single-use self-calling EOAs, selector 0x47b77d1a (one operator) | 81 | almost only NOTUS | 150,964 sat (0.060 USD), min 55,178 | 0.002 gwei, always | 4-189 |

- 122 takes, tips 22,130,077 sat = 8.75 USD (cbLTC 39.55 USD) = 1.25 USD a day for everyone; takes per day 24, 20,
  17, 25, 13, 11, 12.
- One take: median 464,630 gas, 3.60e-6 ETH = 0.0061 USD including the L1 fee (largest L1 fee 1.28e-7 ETH).
- Blocks to take: there is no fixed "takeable" block, the tip grows with pool trading. Gap between two harvests of
  one coin: min 310 s, median 5,172 s, p90 21,446 s. The farm executor replayed before each of the last 24 takes
  already had a gain above 0.020 USD 60 s (300 blocks) earlier in 14 of 24, 5 minutes earlier in 13, 30 minutes
  earlier in 11. Only 3 of 122 takes sit at tx index 2 or lower: not a first-block job.
- Lost attempt: a revert at the cooldown or empty-bucket check costs 44,310 gas (about 0.0005 USD); a NoProfit revert
  after the full path 650,997 gas (about 0.008 USD).

## Limits in the code (bot.py)

- gas limit = `eth_estimateGas` x 1.2, refused above 900,000; `maxFeePerGas` = base fee x 1.25 + 0.0025 gwei,
  refused above 0.05 gwei; cap = limit x maxFee + 3e11 wei L1 allowance; refused at 0.90 USD (ETH taken at 4000 USD).
- fixed priority fee 0.0025 gwei, never raised: at most 25 % of gross.
- after a send (or a paper success) the coin rests for the 300 s cooldown.

## Read cost

120 s timer x 2 coins x 1 `eth_call` (26 CU) = 1,440 calls = 37,440 CU a day, plus about 100 CU per opportunity
(block, estimate, guard call) and 200 CU per send: about 38,000 CU a day = 0.02 USD (1M CU = 0.53 USD). Daily cap in
code 60,000 CU; at the cap it sleeps to 00:00 UTC. No feed filter. The timer is enough because the rivals take
minutes to hours after the tip passes the bot's line.

## Logs (`logs/bot.jsonl`)

`start` (with `executor=`), `check` (per coin: gain or revert name), `opportunity`, `opportunity_skip`,
`paper_sim`, `send`, `send_result` (`result` won / lost, `gas_used`, `gas_cost_wei`, `paid_wei`, `net_wei`,
`winner_block`, `blocks_after_winner`), `signer_reject`, `read_budget`, `check_error`.

## After the trial

7 days live or capital spent: one `attempts` row (sends, wins, net) and lead status `measured` or `blocked_infra`.
Stop early if the launchpad announces a freeze or the two coins stop trading (no `opportunity` line for 3 days).
