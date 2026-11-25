---
type: infra
chains: [ethereum]
protocols: [gho_lending]
author: earner/qwen3.8-flash-next
updated: 2026-11-07
---
# GHO liquidation venues on ethereum: closed as dead_end

All user GHO debt on ethereum mainnet is borrowed through the token's facilitator registry (wiki `mechanism/gho-facilitator-registry.md`); the 2026-11-07 measurement runs (farm-host, 6cffc669, 56d7ca5c; attempts 395-399) mapped all eight facilitators and closed the class:

- **Aave V3 pool venue** (reserve `0xe9ac5231faecb633da0fe85cbb2785b8363427d2`, 310M used = the pool's GHO liquidity): the ONLY venue with user GHO-debt liquidations, ~1.2/day from the ledger `aave_v3.liquidation` source. The three large captures (4.5k/5.0k/37.2k GHO debt) crossed HF < 1 only in the last <=16 blocks before their capture block (getUserAccountData at lookbacks 1/16/64/200/400, attempt 396) - same-block race per `decisions/human/2026-11-06-no-latency-race.md`; the poll-catchable events are dust with gross below gas. dead_end.
- **FlashMinter Facilitator** `0xb639d208bcf0589d54fac24e655c79ec529762b8` (2M cap, 0 used): the GhoFlashMinter flash-fee venue - no standing debt, no liquidations.
- **Three mint/burn wrappers** (Plasma `0x2bd010ab5393ab51b601b99c4b33ba148d9466e9`, GSM-Arbitrum `0x436dccc028322afc355f608cf582b7d7f19fdfed`, GSM-Monad `0x0cb7c2a2ab38aed3e6096631d7dba3dabf237134`, 50M each): the verified `GhoDirectFacilitator` ABI exposes only `mint`/`burn` + roles - remote-chain bridging, no borrow, no liquidation venue on mainnet.
- **Three GhoDirectMinters** (Core `0x5513224daaeabca31af5280727878d52097afa05` 250M cap 135M used, Lido 175M/45M, Horizon 80M/59M): Blockscout-verified implementation `GhoDirectMinter` (e.g. Core impl `0xe4c958de49303c9be571e00582cf9454586de76f`) is a thin Aave-pool injector - `mintAndSupply`/`withdrawAndBurn` are `onlyOwnerOrGuardian`, constructor args pin `poolAddressesProvider 0x2f39d218133AFaB8F2B819B1066c7E434Ad94E9e` (Aave V3 Ethereum) + collector + GHO token. They move bucket GHO INTO the Aave pool reserve: their GHO is liquidated by the Aave venue above, not by a venue of their own.

## The LlamaCore "core venue" hypothesis and its refutation

Attempt 398 hypothesized the 135M Core book sat as GHO debt in the LlamaCore/llamalend market contracts (the 20 contracts of the ledger source `llamalend.liquidate`). Measured 2026-11-07 run 56d7ca5c (`scratch/gho53b/probe2-3.py`): the controller getter `borrowed_token()` returns **crvUSD** (`0xf939e0a03fB07F59A73314E73794be0e57AC1B4E`) on the three event-carrying contracts, and crvUSD/DAI/USDC/WBTC/WETH - **zero GHO** - across all 48 controllers in `scratch/llamalend-rolegate/ctrls.json`. Those Liquidate events (0.57-1.26/day) are crvUSD-architecture liquidations whose windows were already classified same-block-race (big) or dust-below-gas (poll) by attempts 379/381/384.

Pitfall kept: the event field name `stablecoin_received` is the venue's own stablecoin, not GHO - pin the debt asset from a getter (`borrowed_token()` on the crvUSD-controller architecture; `stablecoin()` on some factories) before building any GHO bot.

Verdict: no poll-catchable GHO-debt venue with gross above gas on ethereum mainnet - lead 53 closed dead_end at the lead stage (no bot built), per the net-EV template of `decisions/human/2026-11-07-aave2-dust-ev.md`. Side note: the eight most recent ledger `aave_v3.liquidation` captures on Arbitrum carry no GHO debtAsset; Arbitrum GHO cadence is unmeasured but looks thin.
