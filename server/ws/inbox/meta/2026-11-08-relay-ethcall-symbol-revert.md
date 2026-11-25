# relay eth_call anomaly: symbol() reverts while cast succeeds (run 813bcc3e, earner)

At 2026-11-08 ~09:40Z on lane=research, chain=ethereum, an `eth_call` with
`{"to":"0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48","data":"0x95d8c48c"},"latest"`
(and the same with `input`, with/without `from:"0x0...0"`, with "pending") returned
`execution reverted` (code 3, data 0x) for USDC's `symbol()`, and the same request
against the ethereum fork (9003, block 24776373, "latest") reverted too.
`cast call` against the same relay URL returned "USDC" in the same minute, and
`balanceOf` on the same token via the identical curl path returned a word (zero balance
for the probe address). So a raw curl of a call that geth/anvil says reverts, while
foundry's eth_call of the same call succeeds. Not concluded — the scout did not need
token ABIs and moved on; recording per the human's request (decisions 2026-11-08,
"write the address, lane, time, block you used") that the anomaly is real, with:
address 0xa0b86991... (USDC), lane research, 09:38-09:41Z, block tag "latest" and
"pending" both, chainid 1. Reproduce before fixing anything.
