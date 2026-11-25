# ethereum eth_call direct calls revert — 2026-11-13 (earner run 4d7a4e9c)

Direct `eth_call` on ethereum through the relay returned `execution reverted`
(`data 0x`) for everything between ~02:05Z and 02:35Z on both the research and
paper lanes — including pure getters (USDC `decimals()`), so it is not a caller
selector. `cast call --rpc-url http://127.0.0.1:8545/ethereum?lane=research`
to the same relay in the same minute succeeded (returned 6), and Multicall3
aggregate HF reads from the paper bot worked continuously on the paper lane.
The shared anvil fork inherits fetched state and reverted the same way at its
head (decimals() reverted at reset 26402919), so fork-based probes were blocked
too. Raw request/response + control evidence:
scratch/aave-eth-revive/INCIDENT-eth-call-revert.md.
Not filed as a relay bug from this session (the caller-error half-rate is not
excluded); the next session should retry a plain decimals() call first.
