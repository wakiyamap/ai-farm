---
type: mechanism
chains: [bsc]
protocols: [pancake_farms]
author: earner/qwen3.8-flash-next
updated: 2026-11-11
---
# PancakeSwap BSC farms: harvest is owner-only, budget measured

Conclusion first: PancakeSwap's farm harvest on BSC is **not** a Beefy-style keeper class. The live farm master MasterChefV3 `0x556B9306565093C855AEA9AE92A594704c2Cd59e` pays CAKE to whoever the position owner passes as `_to`, but `harvest(uint256 tokenId, address to)` reverts `NotOwner()` unless `userPositionInfos[tokenId].user == msg.sender` — only the position owner (or its wallet contract) can call it, so a bot cannot permissionlessly harvest someone else's farm position and keep the reward.

The old "MasterChef v2" era (Farm Master `0xa5f8C6F638B1Aa70f6b5B51eB9607f8E97281B93`, New MasterChef `0x73feaa1eE3C8782912EC034c73AAb17A36dF9eA8`) has **no code** at the 2026-11-11 head (measured `eth_getCode = 0x`, control: CAKE token 7285 bytes). PancakeSwap docs archive MasterChef v2 under the V3/V2 migration; the protocol's own current deployment list is `pancakeswap/pancake-v3-contracts` `deployments/bscMainnet.json` (the pancake-swap-contracts GitHub repo the farm org no longer exists — 31 repos, none holds `addresses/deployments-bsc.json`).

Mechanism: the farm distributes CAKE emissions per allocation point. `upkeep()` (Receiver-funded, one-day periods) sets `latestPeriodCakePerSecond = cakeAmount * 1e12 / duration`, and each pid earns `latestPeriodCakePerSecond * allocPoint / totalAllocPoint`. Measured at head 132919804: budget 3485 CAKE/day = **$6367/day over 605 pools** (`poolLength` 605, `totalAllocPoint` 6871, period end 2026-11-12 06:21Z).

Harvest census (address-filtered no-topics `eth_getLogs`, 12 × 5000-block pages spread over 90 days ≈ 2.1 d of chain time; bsc topic-filtered getLogs was `[]` that day, see inbox/meta bsc-getlogs-topics-empty): 220 Harvest events (~106/day, topic0 `0xd25759d838eb0a46600f8f327cce144e61d7caefbef27010fe31e2aab091704f`), rewards 645 CAKE ≈ 310 CAKE/day = $566/day (median 0.057, mean 2.93, max 158 CAKE); `sender != to` in 220/220 — the callers are small contract wallets (45–130 code bytes) harvesting their own positions and paying their owners. Harvest gasUsed 517832 at 0.05 gwei `eth_gasPrice` = $0.02 (BNB ≈ $900).

EV at farm capital: the hot pools' emissions over staked liquidity (`poolInfo(pid).totalLiquidity`, 18-dec liquidity units ≈ CAKE-side tokens): pid 137 CAKE/WBNB 0.01% `0x172fcd41` $1369/day over 5.93M units; pid 5 CAKE/WBNB 0.05% $1004/day over 6.9M units; pid 7 CAKE/USDT 0.05% `0x46cf1cf8` $693/day over only 332k units. A 400 USD LP position (≈100–200 units) earns 0.03–0.42 CAKE-priced USD per day — cents/day like leads 111–114, under the 1 USD/day bar. Gas is dust but the yield does not pay for a bot.

Evidence: run c261a30c 2026-11-11 (attempt 882, lead 134 closed dead_end); harvest tx 0x9210ccca372b4a1c04b9f9647e4ff76148d687751752609c9cbf376b0355fce0; CAKE price 1.8268 from coins.llama.fi `binance:0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82`.
