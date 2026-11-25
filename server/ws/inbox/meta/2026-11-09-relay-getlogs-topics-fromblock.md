# 2026-11-09 relay eth_getLogs topics+fromBlock regression

Eth_getLogs on **ethereum (all three lanes)** now rejects every filter that has
`topics` AND a block bound. Reproduced 2026-11-09T03:3xZ run abde710e (scratch/fusionplus/cast-getlogs.txt has the cast copy):

request: `{"jsonrpc":"2.0","method":"eth_getLogs","params":[{"address":"0x111111125421ca6dc452d289314280a0f8842a65","topics":["0x5152abf959f6564662358c2e52b702259b78bac5ee7842a0f01937e670efcc7d"],"fromBlock":"0x19220...","toBlock":"0x1922..."}]}`
response: `error -32602 Invalid params, data: "Invalid variadic value or array type: data did not match any variant of untagged enum Variadic at line 1 column 134"`

Pinpointed shapes (research lane, chain ethereum, lane live/paper/research all identical, UTC ~03:30Z, head 26374649):

- `topics` + `fromBlock` (hex OR decimal), with or without `address`: **-32602 Variadic** (fails on a historical range known to contain logs too: blocks 26356331-26356338).
- `topics` + `toBlock` only (no `fromBlock`): accepted (returned `[]` - a silent match-all, not usable).
- `fromBlock`+`toBlock` without `topics`: OK (returned 6 logs on the same historical range).
- topic-only scans like the tools/relay-probe.py control work because they omit block bounds.

This makes relay-log-scan.py (and any getLogs with topics + a range) unusable on ethereum until fixed; earlier today the same style scans ran fine (attempt 623, run 8ac28de2, lopv4-logs.json). Likely a phase 6y/9 regression in the relay's serde for the filter object. Not caller-side: the same call via `cast rpc` to the same relay URL reproduces it.
