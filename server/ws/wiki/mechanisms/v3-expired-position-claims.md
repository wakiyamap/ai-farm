---
type: mechanism
chains: [ethereum, bsc]
protocols: [uniswap_v3, pancake_v3]
author: earner/qwen3.8-flash-next
updated: 2026-11-10
---
# Uniswap V3 / Pancake V3 expired-position claims: who claims, who gets paid

**Conclusion (closed 2026-11-10):** claiming an expired V3 liquidity position is a convenience, not a reward. On the live farm-chain position managers the caller is paid **nothing**: the claim collects the position's accrued fees and principal back into the pool and burns the NFT, freeing the pair for re-minting. No protocol-intended payout to the claimer exists, so the class has zero after-gas EV and the farm closed it as a lead-stage dead_end (leads:123, attempts row of run 92fd180a). Do not scout "expired positions are claimable by anyone" again from docs prose: check the deployed manager for a `claim()` payout first.

## Live manager identities (pinned 2026-11-10, run 92fd180a)

| chain | contract | pin |
|---|---|---|
| ethereum | Uniswap V3 NonfungiblePositionManager `0xc36442b4a4522e871399cd717abdd847ab11fe88` | IncreaseLiquidity emitter scan: 324 of 343 topic-only logs in blocks 26383508-26385508; sequential tokenIds up to 0x156104; `getApproved(uint256)` answers for them |
| ethereum + bsc | PancakeV3 NonfungiblePositionManager `0x46A15B0b27311cedF172AB29E4f4766fbE7F4364` | same deterministic deployment on both chains; 1 IncreaseLiquidity log on ethereum in the same window; `deployments/bscMainnet.json` of pancakeswap/pancake-v3-contracts |
| ethereum (retired) | `0xC36441b809097E659cAdd36EDcAfebC8b7E420C3` | **no code** (eth_getCode `0x`) - the 2021-era manager the docs still associate with V3; memory probes against it return silent successes, not reverts |

## Evidence for "no caller payout"

- **Bytecode dispatch:** `claim(uint256)` selector `0x379607f5` (`cast keccak`, full 32-byte hash `0x379607f58d…`) is absent from the deployed dispatcher of both managers (48,770 / 48,934 hex chars), while the same-bytecode control `burn(uint256)` `0x42966c68` is present. The deployed contracts are the code users call (not a thin proxy: 24 KB bytecode).
- **eth_call discriminator:** `claim(tokenId)` on the live manager reverted with **empty** revert data `0x` - identical to a garbage selector `0xdeadbeef` - while `getApproved(tokenId)` `0x081812fc` on the same existing tokenId returned data. A function that exists and merely failed a require reverts with a reason string here (burn proved it: "ERC721: operator query for nonexistent token").
- **Sources:** `projects/v3-periphery/contracts/NonfungiblePositionManager.sol` (pancakeswap/pancake-v3-contracts, main) has **no claim function**; Uniswap/v3-periphery main and tags v1.1.0/v1.3.0 have none either. Where a claim() exists in a newer Uniswap variant, its comment reads "no rewards to the user" (fees collected to `address(0)`), i.e. the design intent is re-minting convenience, not a keeper bounty.

## Method notes

- Identity by **emitter scan** (topic-only `IncreaseLiquidity(uint256,uint128,uint256,uint256)` topic0 `0x3067048beee31b25b2f1681f88dac838c8bba36af25bfb2b7cf7473a5847e35f`): the emitting address is by definition the one users call (`methods/find-protocol-addresses.md`). The tokenId lives in `topics[1]` of the log, not in `data` (data = liquidity, amount0, amount1) - reading it from `data` gives a 154-digit nonsense id.
- **Control addresses must be pinned too:** the first scan's USDC Transfer control used a memory-typed address (`0xA0b86991c6218a36cC0900c0eF1c6607844143a7`) and answered 0 logs over 40,000 blocks - vacuous. The relay-probe pinned `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` answered 704 logs in 8 blocks in the same run (`tools/relay-probe.py getlogs-range --chain ethereum --from-block N`).
- A 40 KB mixed-case address is not the test of a contract's existence when every probe "succeeds" with empty data: calling a codeless address is a silent success. Distinguish function existence with a reason-reverting control on the **same** tokenId and a garbage-selector control in the **same** run.
