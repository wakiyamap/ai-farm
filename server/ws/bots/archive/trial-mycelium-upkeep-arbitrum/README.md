trial: hourly public upkeep reward of the Tracer / Mycelium Perpetual Pools PoolKeeper on Arbitrum, sent on a timer with no priority fee.

## What pays

`PoolKeeper.performUpkeepSinglePool(pool)` (keeper `0x759e817F0C40B11C775d1071D466B5fF5c6ce28e`, verified source) has no
access control. Once `pool.intervalPassed()` (`lastPriceTimestamp + updateInterval`, 3600 s on pool
`0x3a52ad74006d927e3471746d4eac73c9366974ee`) it runs the pool upkeep and pays `msg.sender` from the pool balances:
gas spent x `PoolKeeper.gasPrice()` (a stored 3 gwei, the chain base fee is 0.02 gwei) x ETH price x 1.05 (+0.05 per 13 s
late, cap 2.0), in the quote token USDC.e `0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8`. Called early it pays nothing.
Median reward 0.83 USDC.e; USDC.e is not counted as funds, so the executor sells it for USDC in the same transaction on
the Uniswap V3 0.01 pct pool `0x8e295789c9465487074a65b1ae9ce0351172393f` (factory `0x1F98431c8aD98523631AE4a59f267346ea31F984`
getPool(USDC, USDC.e, 100); token0 USDC, token1 USDC.e; 4.9k USDC / 22.5k USDC.e).

## Competition, last 7 days

- 170 KeeperPaid in 7 d (blocks 523,415,978-525,485,978), 5 rewarded addresses; newest 44 takes (blocks
  524,996,772-525,696,772, `scratch/eqb/tracer-fee.json`): senders `0x72e5d0033d10ba0b526104c4c9ecb7621b6392e4` 23 (via
  `0x84450c61...`, priority 1.85 gwei), `0x91e93002f68848ed3ba114c338078e0c50647a44` 13 (via `0xdaf506b4...`, 1.66-1.83 gwei),
  EOA `0xac7fa3f3a20365aa60cab977979f8c4388c6d21d` 6 (direct, 0.6 gwei), `0x45268e7f...` 1 and `0xea388808...` 1 (3.3-3.5 gwei,
  the 2.5M-gas upkeeps).
- Blocks to take: 0. All 44 takes are in the block whose timestamp equals previous upkeep + 3600 s; tx index 1 in 41,
  2 in 2, 11 in 1.
- Priority-fee level: winners pay 0.6-3.6 gwei (median 1.85) and the fee is charged, but it did not decide position:
  in blocks 525,544,232 and 525,581,426 the 0.6 gwei EOA is at index 1 and the 1.85 gwei and 1.83 gwei senders are behind
  it (index 2-3 or the next block, reverted at 29,145 / 33,396 gas) (`scratch/eqb/blkpeek.py`). Position follows arrival
  at the sequencer.
- Others already send with no tip and lose on timing: `0x2c89bc76...` puts 20 calls into the block one second before the
  due second, `0xcd18ecda...` about 2 per block for a second after the take.

## What the bot does

Timer only (no feed, no per-block polling). It reads `lastPriceTimestamp` every 10 min at most; 20 s before the due
second it simulates the take for the due second (`eth_call` with block override `time`, which the relay's Arbitrum node
accepts) and estimates gas the same way. In live mode it then hands `SEND_OFFSETS_S` (default -1.6, -1.45, -1.3, -1.15,
-1.0 s relative to the due second, plus `state/bias.json`) executor calls to the signer, with priority fee 0 and
maxFeePerGas = 2 x base fee. The lead is the signer latency measured on the farm's first timer send (1.25 s,
`methods/timer-first-block-send.md`) plus about one 0.25 s Arbitrum block, so the sends should reach the sequencer
from about 0.35 s before to 0.25 s after the due second; every `send` row logs `signer_s`. A send that lands in a block
of the previous second reverts NotDue (34,000 gas). If the signer handles the five requests one after another instead
of in parallel, only the first is well timed: set `SEND_OFFSETS_S` to fewer sends then.
After the window it logs the winner (`window_result`) and, per send, `send_result` won / lost, gas used, its block and
the winner's block and index. If every send of a window was early (or every one late) the bias moves 0.1 s later (earlier),
within -2..+1 s. If nobody takes the upkeep at the due second it sends one call right away (`overdue`).

Cost: a lost send is about 34,000 gas x 0.02-0.04 gwei = 0.0012-0.0025 USD; five per hour is at most 0.15-0.3 USD per
day. A won take is about 350,000 gas = 0.013 USD against about 0.75 USDC received.

## Read cost

About 13,500 Alchemy CU/day live (24 windows x about 400 CU + 144 idle reads x 26 CU) = 0.007 USD/day at 1M CU =
0.53 USD. Code cap 60,000 CU/day.

## Result to write after 7 days live

sends, wins, net USDC, and the distribution of `position` / `blocks_from_winner`; `measured` with the win rate, or
`blocked_infra` with how many blocks late the best bias still was.

## Fork proof

`scratch/trial-mycelium-upkeep-arbitrum/proof.py` (see manifest `fork_evidence`).
