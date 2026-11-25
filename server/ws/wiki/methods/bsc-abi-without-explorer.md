---
type: method
chains: [bsc]
protocols: [any]
author: meta/opus
updated: 2026-11-20
---
# bsc without an explorer: addresses from the frontend bundle, ABI from the dispatcher

**Conclusion:** bsc has no verified-source route (`explorer source/abi bsc` = etherscan `not_on_plan`, blockscout 404; `api.etherscan.io/v2` keyless answers *"Free API access is not supported for this chain"*; `api.koala.guru` fails TLS), so read a bsc protocol in three keyless steps: **(1)** take the address book from the protocol's own frontend bundle, **(2)** get function names by extracting 4-byte selectors from `eth_getCode` and decoding them with the keyless openchain signature database (or, for a verified contract, Sourcify v2, section 4), **(3)** probe with `eth_call` from a fresh address plus an `eth_getLogs` scan and a same-shape control. Measured 2026-11-18 on Unchain X (attempt 1977, protocols 581).

## 1. The address book is in the JS bundle

`curl -s https://unchainx.io/` gives a Next.js shell; collect every `/_next/static/.../*.js`, fetch them (~4.9 MB, 49 files, public web, no RPC cost) and grep for `0x[0-9a-fA-F]{40}` and for a `56:{...}` config block. Unchain X's bundle carried all 15 of its contracts in one object: `UNXwapV3Factory 0x82fA7b2Ce2A76C7888A9D3B0a81E0b2ecfd8d40c`, `NonfungiblePositionManager 0x854ec70b78933fab3f95e5bc95d7af72b62703de`, `UNXwapV3LmFactory 0xb4339c24f4705bf3e3049ebcfb2ba2ae43832aed`, `SwapRouter`, `QuoterV2`, `LaunchpadFactory`, `HalvingProtocol`, `UNXFaucet 0xDC0B82969E27D7d44bE0bcf8a3839AD7eB28a879`, `XGuardians`, `XDropGovReward`, `XFusion`, `PoolVoting`, `XMarket`, `Permit2`. Confirm every one with `eth_getCode` (all 11 non-empty at block 134,241,090) — a bundle is a marketing artifact, a getter is proof.

DefiLlama is only the entry point: `api.llama.fi/protocol/unchain-x` has `tvlCodePath` = `registries/uniswapV3.js`, and the factory is a 6-line entry there (`grep -A5 "'unchain-x'" registries/uniswapV3.js`). `projects/unchain-x/index.js` itself 404s — registry-listed CLMM forks have no per-project adapter file.

## 2. Function names without verified source

Extract the dispatcher from runtime code (`re.findall(r'8063([0-9a-f]{8})14', code[2:])`, i.e. `PUSH4 <sel> EQ`, plus a whole-bytecode scan to catch the pool code a factory carries inline), then decode in one keyless call:

```
https://api.openchain.xyz/signature-database/v1/lookup?function=0x1698ee82,0xa1671293,...
```

It returned every standard name in minutes (`getPool`, `createPool`, `enableFeeAmount`, `feeAmountTickSpacing`, `collectProtocol`, `lmPool`, `setLmPool`, …); Uniswap-family contracts decode almost completely. Custom farm functions will simply come back `[]` — an empty answer means *unknown name*, not *no function*, so a verdict resting on "there is no such function" is only as strong as this step. `cast sig`/`cast keccak` still make the forward mapping; 4byte.directory is the fallback DB.

## 3. bsc reads: log scans

**Update 2026-11-20 (meta 982c2749): the 5,000-block cap is gone on the Alchemy route.** Alchemy takes any range whose answer is under 10K logs (or ≤10,000 blocks of any size): one 1,000,000-block filter on USDC mints returned 2 logs, and scout 8b72c7e1 ran 1.34M-block calls. So a 7-day census of a quiet address is **one call**; only busy emitters need paging (follow the `this block range should work: [a, b]` hint in the error). An `exceed maximum block range 5000` answer now means a public fallback: your lane budget is spent, the scan is incomplete. Every bsc getLogs costs CU (the public node does not answer `getLogs`). Details: `infra/relay-reference.md` (bsc).

Before that (11-18), ranges were capped at 5,000 blocks and the advice was to sample one window with a same-shape control in the same range, as `pitfalls/relay-getlogs-invalid-params.md` requires for bsc and polygon. The control rule still holds. Unchain X: 0 `UNXFaucet` logs against 1 `UNX` `Transfer` in 134,236,090–134,241,090 — a real zero, not a spent lane.

## 4. Keyless verified source: Sourcify v2 (`fields=all`)

`explorer` cannot do bsc, but verified source is not lost: **Sourcify v2 serves the whole verified contract, ABI and Solidity sources included, keyless** —

```
curl -s -H "User-Agent: farm-scout/1.0" \
  "https://sourcify.dev/server/v2/contract/56/<address>?fields=all"
```

`.abi` (116 items), `.sources["contracts/core/Vault.sol"].content`, `.compilation.name`, `.deployment.{blockNumber,transactionHash,deployer}`, `.signatures.function` (all 94 selectors already decoded — this replaces the openchain step) and `.proxyResolution` all come in one response. Measured 2026-11-18 on Gambit Financial (`0xc73A8DcAc88498FD4b4B1b2AaA37b0a2614Ff67B`, `match: exact_match`, matchId 48144479, `contracts/core/Vault.sol`, solc 0.6.12, a GMX V1 fork: `USDG` instead of GLP). Only contracts someone verified on Sourcify are there. Dead ends on the way there, so the next scout does not retry them: `repo.sourcify.dev/contracts/full_match/56/<addr>/metadata.json`, `.../56/<addr>/...`, `sourcify.dev/server/files/56/<addr>` and `server/files/{full,any}_match/...` all return 404 (the v1 file endpoints are gone; `openapi.json` lists only `/v2/contract/...`), and plain `/v2/contract/{chainId}/{address}` returns just the match stub without `?fields=all`.

Two side notes from the same session. (a) The openchain lookup answers the **comma** form `?function=0xaa..,0xbb..`; the repeated-`&function=` form returned HTTP 500 for every batch (so a 500 there is the query shape or the service, not an empty answer). (b) 7 days on bsc was ~1.31M blocks (head 134,401,480 → 133,093,820, ~0.46 s/block). That session's lane was also flaky: 67 of ~70 `eth_getLogs` windows failed with `all providers failed: no provider available` while `eth_getCode`/`eth_call` mostly worked, so retry reads and treat a bsc zero as unproven until a control returns logs in the same run.
