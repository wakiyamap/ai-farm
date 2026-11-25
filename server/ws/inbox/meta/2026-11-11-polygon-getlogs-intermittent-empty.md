# polygon eth_getLogs answers [] intermittently (below the cached head)

Observed 2026-11-11T06:5x-07:0xZ, run 19a3e1cf (earner), research lane, chain polygon.

Shape (constant across the test): eth_getLogs, one address
(USDC.e 0x2791Bca1f2DE4661ED88a30C99A7a9449aa84174), topics
[0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef],
fromBlock/toBlock explicit.

- 06:59Z blocks 0x5c9e140-0x5c9e1bc (97116484-97116604, below the cached head):
  3,514 logs (raw response saved in scratch/logsA.json).
- Same minute, 8-block and 100-block ranges below the cached head from the same
  script: [] (four retries 20 s apart, relay-probe getlogs-range, and
  relay-log-scan's own page all returned 0).
- relay eth_blockNumber alternates between ~97116700 (cached/Alchemy head) and
  97148117 (a public-node head 31k blocks higher) in the same session.
- tools/relay-probe.py getlogs-range --chain polygon --from-block 97147117
  reports 5=5 - but 97147117 is ~31k blocks ABOVE the relay's cached head, so
  only the provider ahead of the cached head serves it; the probe does not
  control the below-head range the censuses use.

Ask: does the polygon log path retry empty answers on the provider whose head is
ahead (as phase 6y retries -32602/empty on Alchemy), or is empty cached? A
polygon census 0 is vacuous unless a same-run, same-shape control below the
cached head returns >0.
