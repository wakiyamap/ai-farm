---
type: method
chains: [bsc]
protocols: [any]
---
# bsc without an explorer: addresses from the frontend bundle, ABI from the dispatcher

**Conclusion:** bsc has no verified-source route (`explorer source/abi bsc` = etherscan `not_on_plan`, blockscout 404; `api.etherscan.io/v2` keyless answers *"Free API access is not supported for this chain"*; `api.koala.guru` fails TLS), so read a bsc protocol in three keyless steps: **(1)** take the address book from the protocol's own frontend bundle, **(2)** get function names by extracting 4-byte selectors from `eth_getCode` and decoding them with the keyless openchain signature database, **(3)** probe with `eth_call` from a fresh address plus a short `eth_getLogs` range and a same-shape control. Measured 2026-11-18 on Unchain X (attempt 1977, protocols 581).

## 1. The address book is in the JS bundle

`curl -s https://unchainx.io/` gives a Next.js shell; collect every `/_next/static/.../*.js`, fetch them (~4.9 MB, 49 files, public web, no RPC cost) and grep for `0x[0-9a-fA-F]{40}` and for a `56:{...}` config block. Unchain X's bundle carried all 15 of its contracts in one object: `UNXwapV3Factory 0x82fA7b2Ce2A76C7888A9D3B0a81E0b2ecfd8d40c`, `NonfungiblePositionManager 0x854ec70b78933fab3f95e5bc95d7af72b62703de`, `UNXwapV3LmFactory 0xb4339c24f4705bf3e3049ebcfb2ba2ae43832aed`, `SwapRouter`, `QuoterV2`, `LaunchpadFactory`, `HalvingProtocol`, `UNXFaucet 0xDC0B82969E27D7d44bE0bcf8a3839AD7eB28a879`, `XGuardians`, `XDropGovReward`, `XFusion`, `PoolVoting`, `XMarket`, `Permit2`. Confirm every one with `eth_getCode` (all 11 non-empty at block 134,241,090) — a bundle is a marketing artifact, a getter is proof.

DefiLlama is only the entry point: `api.llama.fi/protocol/unchain-x` has `tvlCodePath` = `registries/uniswapV3.js`, and the factory is a 6-line entry there (`grep -A5 "'unchain-x'" registries/uniswapV3.js`). `projects/unchain-x/index.js` itself 404s — registry-listed CLMM forks have no per-project adapter file.

## 2. Function names without verified source

Extract the dispatcher from runtime code (`re.findall(r'8063([0-9a-f]{8})14', code[2:])`, i.e. `PUSH4 <sel> EQ`, plus a whole-bytecode scan to catch the pool code a factory carries inline), then decode in one keyless call:

```
https://api.openchain.xyz/signature-database/v1/lookup?function=0x1698ee82,0xa1671293,...
```

It returned every standard name in minutes (`getPool`, `createPool`, `enableFeeAmount`, `feeAmountTickSpacing`, `collectProtocol`, `lmPool`, `setLmPool`, …); Uniswap-family contracts decode almost completely. Custom farm functions will simply come back `[]` — an empty answer means *unknown name*, not *no function*, so a verdict resting on "there is no such function" is only as strong as this step. `cast sig`/`cast keccak` still make the forward mapping; 4byte.directory is the fallback DB.

## 3. bsc reads: the range cap decides the census

bsc `eth_getLogs` ranges are capped at 5,000 blocks and every call costs CU (the public node does not answer `getLogs`), while 7 days is ~800k blocks — a full week census is 160+ calls. Sample instead: one 5,000-block window (~1 h at bsc block times) with a same-shape control in the same range, exactly as `pitfalls/relay-getlogs-invalid-params.md` requires for bsc and polygon. Unchain X: 0 `UNXFaucet` logs against 1 `UNX` `Transfer` in 134,236,090–134,241,090 — a real zero, not a spent lane.
