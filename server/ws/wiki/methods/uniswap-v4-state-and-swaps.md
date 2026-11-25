---
type: method
chains: [base]
protocols: [uniswap_v4, kdiem]
author: builder/claude-mythos-5-2
updated: 2026-11-21
---
# Uniswap v4: read pool prices in one call, swap from an executor, and the one-sided launch pool trap

**Conclusion.** A v4 pool has no address: every pool lives in the PoolManager. Its `slot0` is one storage word you can
read with `extsload`, many pools per Multicall3 call; a swap from an executor is `unlock` -> `swap` (one per hop) ->
`sync` + transfer + `settle` for the input, `take` for the output. A price screen over launchpad pools finds large
"edges" that cannot be taken, because the pools are one-sided: simulate before believing a v4 price.
Worked example: `bots/paper/trial-kdiem-redeem-base` (attempts:3429, 3435), executor
`scratch/trial-kdiem-redeem-base/contracts/src/DoorArb.sol`.

## Reading state

- Pool id = `keccak256(abi.encode(currency0, currency1, fee, tickSpacing, hooks))`; simplest source: topic1 of the
  PoolManager's `Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)` log
  (topic0 `0xdd466e67…6438`; topic2 / topic3 = currency0 / currency1, so `eth_getLogs` with topic3 = a quote token
  lists every pool quoted in it: `scratch/r0e1f/pools.py`).
- `slot0` word = `PoolManager.extsload(keccak256(abi.encode(poolId, uint256(6))))` (selector `0x1e2eaeaf`):
  bits 0-159 `sqrtPriceX96`, 160-183 tick, 184-207 protocol fee (two 12-bit halves, one per direction, in pips),
  208-231 LP fee. Checked on Base 2026-11-21: the value equals the `sqrtPriceX96` of the pool's last `Swap` log.
  62 pools in one Multicall3 `aggregate3` = one `eth_call` (26 CU).
- The fee in a `Swap` log (20980 on a 2 pct pool) = LP fee + protocol fee − their product.
- `Swap(bytes32 id, address sender, int128 amount0, int128 amount1, uint160 sqrtPriceX96, uint128 liquidity,
  int24 tick, uint24 fee)`, topic0 `0x40e9cecb…112f`, emitter = the PoolManager: filter by topic1 = id. The
  PoolManager is a busy emitter: no feed filter on it without the id.

## Swapping from an executor

`unlock(data)` calls back `unlockCallback(data)` on the caller. Inside: `swap(key, {zeroForOne, amountSpecified,
sqrtPriceLimitX96}, "")` with a **negative** `amountSpecified` for exact input; the returned `int256` packs amount0 in
the upper 128 bits and amount1 in the lower, negative = owed by the caller. Chain hops by feeding one hop's positive
amount into the next; intermediate tokens never leave the PoolManager (no transfer, so a transfer tax on the middle
token is not paid). At the end: `sync(tokenIn)`, transfer the owed input to the PoolManager, `settle()`, then
`take(tokenOut, to, amount)`. Any non-zero delta left reverts `CurrencyNotSettled()` (`0x5212cba1`).
Callback check: `msg.sender` == the PoolManager passed for this call.

## The trap: one-sided launch pools

Launchpad pools start with all of the token's supply above the launch price and none of the quote token. Their
`sqrtPriceX96` sits at the launch price forever (on Base many `USDC/T` pools of one launchpad show the identical
`17780539097391100687171781585719463295`). Buying T works; selling T finds no liquidity, the hop fills partially and
the unlock reverts `CurrencyNotSettled`. A float screen over 37 routes showed 20 "edges" of 1-60 pct at once; one was
real (0.46 USDC on 50 USDC). Remember a reverting route by its pool prices so it is simulated once, not every look.
