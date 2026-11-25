---
type: infra
chains: [ethereum]
protocols: [llamaLend]
---
# LlamaLend (crvUSD loans): big debt book, stale sources, likely role gate

LlamaLend mainnet is the biggest debt book on the farm chains nobody has measured: about **43.6M USD borrowed** on ethereum (DefiLlama `curve-llamalend` chainTvls "Ethereum-borrowed", latest series point 2026-11-06; 66 pools). Before building a liquidation bot here, answer one gate question from **live** source: the LlamaLend org sources show liquidators kept in a **whitelist** (`addLiquidator`, `LiquidatorAdded(address)`), like GMX v2 keepers - if the live system keeps that gate, the class is role-gated and out of scope per `decisions/human/2026-11-06-no-latency-race.md` without any measurement.

## What the 2026-11-06 scout (run 3ce73b32) pinned and could not pin

- The org repos are stale for the live chain: `LlamaLend/contracts` master (frozen 2024-05-17) is the old `LendingPool.sol` design; its event topics computed from the source signatures - `LoanCreated(uint256,address,uint256,uint256,uint256,uint216)` `0x01914841c62f87956b32077d1a97c57580e20eba1f51dd24d7a759bcab99351e` and `LoansRepaid(uint256,uint256,address)` `0x3da2f9ee1e6b0868c9fc585cf88c8ca0bad1bcb2bfbcce9e8aac714d3d4669cf` - returned **zero events** in an unfiltered topic-only relay research scan of blocks 26258174-26358173 (100k blocks, 14 days, head 26358173). The live deployment runs a newer architecture than any org source.
- The old-architecture factory `0x55f9f26b3d7a4459205c70994c11775629530ea5` (pinned from `LlamaLend/interface` repo `main` branch `lib/constants.ts` `FACTORY_MAINNET`, repo updated 2026-08-20 - not from memory) has code and `owner()` returns `0x1b4330a7e65cd18bcc668a83a6d27f915e60670b`, but `totalBorrows()`, `getLiquidators()` and `liquidators()` all revert: the repo pool getters are not on it. Do not treat this address as the live liquidation venue.
- External tools on this host: harness `web_search` has no API key, `docs.llama.finance` fails DNS, `api.llama.fi/registry` and `/tokenHolders` are route-not-found (see `inbox/meta/host-dns-allowlist.md`, `inbox/meta/b2176d12-websearch-no-apikey.md`). `api.github.com` and `raw.githubusercontent.com` work - pin contract facts from the org repos through them, not from web search.

Next measurement per `attempts:329` / `leads:35`: confirm the whitelist gate on the live contracts; if `liquidate()` is public, measure Liquidation events/day and repay size with the NEW architecture signatures, then net-EV per batch at floor gas before any bot.
