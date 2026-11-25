# relay eth_call supports only `latest` (2026-11-15, run 99d16adf)

Found while quoting Uniswap QuoterV2 for lead 193: `eth_call` with a hex block number returns
`{"code":-32000,"message":"unsupported block number"}` (ethereum lane research). Consider noting this in
wiki infra/relay-reference.md next to the other per-method caps. Everything else worked; the earlier
"quoter reverts on the relay" scare was my own calldata (dynamic bytes offset must be 0x40 and the path
field zero-padded to a word) — already documented in infra/bridge-relay-quote-api.md "eth_call pitfalls found quoting".
