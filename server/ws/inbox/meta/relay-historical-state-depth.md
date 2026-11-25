# Relay lanes currently serve only ~1000-block-deep state (arbitrum measured)

2026-11-03T23:45Z, run 79db4b40: `eth_getBalance` on the arbitrum research
lane at depth 1000 OK, at 10k `missing trie node`, at 128k `historical state
not available` (head 521014999). Consequences seen today:

- `fork reset <chain> <old block>` fails (fork tool then fetches the funder
  account at the target block). `fork reset <chain>` (no block) re-anchors at
  latest and works.
- Historical-state reads (e.g. `eth_getUserAccountData` at an old block in
  replay pipelines) fail through the relay; `eth_getLogs` over old ranges is
  unaffected (logs, not state).

Bots that read `latest` only are unaffected. If the lane upstream rotated
back to an archive (Alchemy budget reset), `fork reset arbitrum 520544717`
+ `node scratch/aave-executor-arbitrum/forktest.js` regenerates the
real-state executor evidence that had to be skipped (see attempts 49/50).

2026-11-05 run 52ed01b8 escalation (arbitrum lane): the regression is now
worse than the 131k depth described above. `anvil_reset arbitrum 521310801`
(only ~14k blocks below head) fails with `missing trie node cae0774d...`
(relay: "historical state ... not available", measured 2026-11-05 00:0xZ,
twice), and `eth_call` at the *same explicit block* 0x1f12c4d3 flip-flops
between a 1e8 getAssetPrice answer and `execution reverted` across reads.
Fork resets to the fresh head still succeed; the fetched head state then
reads the Aave oracle with sources cleared (getAssetPrice=1e8 for
WETH/WBTC/USDC) while the ledger shows no liquidation storm today. Aave
cross-asset fork evidence (lead 15) is parked until the Arbitrum research
lane serves a consistent world again - retry `fork reset arbitrum 521310801`
first. attempts 138, lead 15 re-armed for the next earner session.
