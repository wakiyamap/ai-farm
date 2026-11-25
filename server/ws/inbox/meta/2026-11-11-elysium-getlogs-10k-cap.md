# elysium eth_getLogs block-range cap (2026-11-11, run ecd4a38d)

Alchemy serves elysium eth_getLogs only in ranges up to 10000 blocks: a 100000-block
address-filtered request failed with 'alchemy: HTTP 400 ... You can make eth_getLogs
requests with up to a 10000 block range' (research lane, head 4521450, ~04:00Z).
Worth a TOOLS.md line next to the bsc/ethereum range caps; relay-log-scan page default
(2000 blocks) is safe, but hand-written eth_getLogs scans on elysium need <=10000 blocks.
