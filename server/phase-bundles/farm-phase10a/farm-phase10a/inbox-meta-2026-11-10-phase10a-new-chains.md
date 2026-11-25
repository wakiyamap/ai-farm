# Five new chains on the read side (phase 10a, human, 2026-11-10)

The farm now works on eight chains. New: `bsc` (BNB Smart Chain, 56), `polygon` (Polygon PoS, 137),
`avalanche` (Avalanche C-Chain, 43114), `optimism` (OP Mainnet, 10), `hyperevm` (HyperEVM, 999).

What works on them now:
- relay: `http://127.0.0.1:8545/<chain>?lane=...` (same lanes and budgets as before)
- forks: `fork status|reset|deploy|... <chain>`, ports 9004 bsc, 9005 polygon, 9006 avalanche,
  9007 optimism, 9008 hyperevm (reachable by the earner and paper bots)
- ledger: `ledger add-source` accepts the new chain names; ledger-ingest skips a chain whose head
  is unreadable instead of failing the whole run
- kb: `chain` may be any of the eight

What does not work yet: `gate promote` refuses manifests whose chains include a new one. Funding,
signing and the watchdog for these chains come in a later phase (10b).

Differences worth putting where agents read them:
- USDC on BNB Smart Chain has 18 decimals (6 elsewhere)
- Alchemy has no `trace_*` on Polygon and HyperEVM
- the public BNB node does not serve `eth_getLogs`; log scans there cost Alchemy CU
- native tokens: BNB, POL (formerly MATIC), AVAX, ETH (OP Mainnet), HYPE
- Chainlink price feeds: use the Standard proxies, not SVR

Please update TOOLS.md and any role file that lists "base / arbitrum / ethereum" as the whole set
(fork chain list, ledger examples). common.md is already updated.
