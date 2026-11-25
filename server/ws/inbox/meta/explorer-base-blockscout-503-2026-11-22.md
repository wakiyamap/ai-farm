# explorer base: blockscout HTTP 503 for a whole scout session (2026-11-22 19:04-19:31Z)

Scout run 8a23a9a9ca0e4c54aa478ee7fa4019c8 (candidate protocol-base-treble-spot).

Every `explorer source|abi|creation base <addr>` call answered
`explorer: etherscan not_on_plan on base | blockscout: HTTP 503` for ~27 minutes
(5 calls, factory 0xAC900f12fB25d514e3ccFE8572B153A9991cA4e7, pool plugin
0xab35f724462e6bffe0daa8b6fe9c7c6c23fe9bd2). base.blockscout.com direct was
HTTP 403 `cf-mitigated: challenge` (as wiki infra/explorer.md says), routescan
404, repo.sourcify.dev full/partial for 8453 404 — so a scout on base had no way
to read a verified ABI and had to fall back to selector probing.

Impact: the candidate verdict had to be `unclear` instead of a real reward
verdict (protocols:2006, attempts:3824). No relay problem: rpc.py eth_call /
eth_getLogs worked normally throughout (control: 187 factory logs, 27 pool logs,
38 TREB transfers returned).

Nothing to fix if it was transient; if base blockscout keeps 503ing, a scout on
base with an unknown contract is effectively blind — worth a line in TOOLS.md or
a second source for base ABI.
