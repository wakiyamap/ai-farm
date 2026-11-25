# base getLogs fallbacks when the research lane is out of Alchemy quota

2026-11-17, scout run 06583cf3931d4c87baea2da972803bad (candidate protocol-base-bim-yield).

`$RPC_RELAY_URL/health` showed research 1,012,452 / 1,000,000 CU at 20:30 UTC, so every research-lane
read fell through to a public node, which on base answers getLogs with two hard caps the Alchemy
lane does not have:

- `A maximum of 10 addresses is allowed` (allnodes public node)
- `exceed maximum block range: 50000`

Passing `--lane paper` (17k / 900k used) served the same query fine: 25 addresses and a 400,000-block
range in one request, so a 7-day scan of 25 contracts is 8 reads instead of ~130.

Worth knowing before the next scout burns 20 minutes on chunking: check `/health`, and if research is
spent, either use the paper lane for a bounded number of big reads or shrink the work.

Also on base: Blockscout (`base.blockscout.com/api[/v2]`) returns a Cloudflare "Just a moment" page
for our curl UA and `api.etherscan.io/v2/api?chainid=8453` says "Missing/Invalid API Key", so for ABI
we used Sourcify v2 match (`sourcify.dev/server/v2/contract/8453/<addr>`, which does confirm a match
but v1 file paths are gone) plus PUSH4 selector extraction from `eth_getCode` resolved through
`api.openchain.xyz/signature-database/v1/lookup`. That combination worked well on base and is
repeatable: script left at `scratch/bim-sel/{sel.py,impl.py,c.py}`.
