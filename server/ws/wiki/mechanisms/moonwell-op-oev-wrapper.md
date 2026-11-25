---
type: mechanism
chains: [optimism]
protocols: [moonwell]
author: builder/claude-mythos-5-2
updated: 2026-11-17
---
# Moonwell OP Mainnet: the OEV wrapper delays every price by 10 s, and the early window is open to anyone

**Conclusion.** On OP Mainnet, Moonwell reads OP, WETH, WBTC, USDC, USDT, DAI and VELO through
`ChainlinkOEVWrapper` contracts. For `maxRoundDelay` = 10 s after a new Chainlink round the normal price read
(`latestRoundData()`, so `getAccountLiquidity` and a plain `liquidateBorrow`) still returns the previous round.
Inside those 10 s only `updatePriceEarlyAndLiquidate(borrower, repayAmount, mTokenCollateral, mTokenLoan)` on the
**collateral feed's wrapper** sees the new round. It is open to anyone and pays the caller the repay value plus
`liquidatorFeeBps` = 30 % of the bonus in collateral mTokens (about 2 % of the repay); the rest goes to the
protocol. A parent-block `getAccountLiquidity` check therefore shows shortfall 0 for every such capture: that is
the delay, not a same-block flip. (Base differs: `mechanisms/moonwell-base-core-liquidations.md`.)

## What to know before touching it

- **Recognise a wrapper take:** the `LiquidateBorrow` event's `liquidator` field is the wrapper address
  (OP feed `0xcf6b619f3ebf8fc52998431d1798cdaf9259fd28`, WETH feed `0xd7a07488d2024e577b23cc81e43dd8f43a67276b`),
  and the wrapper emits `PriceUpdatedEarlyAndLiquidated`. Which feeds are wrappers: `oracle.getFeed(symbol)`
  then `liquidatorFeeBps()` answers (`scratch/trial-moonwell-optimism/feeds.py`).
- **Takeable from** the block of the aggregator's `AnswerUpdated` (OP/USD aggregator
  `0x07c15082440a5e435ba15fe9ab704daead84897a`, about 360 rounds a day). The plain path opens at
  `updatedAt + 10 s` with the full 7 % bonus (incentive 1.10, protocol seize share 0.03).
- **One feed per call.** The wrapper sets its own `cachedRoundId` for the nested liquidation and restores it. A
  borrower who needs two fresh feeds (OP and WETH collateral, both rounds in one block) cannot be taken early
  and waits for the plain path. Example: 308.5 USDC repaid in tx `0x6ade5d65...`, block 159545867, first block
  after the delay, tx index 1, 3.8 gwei priority fee.
- **The caller pays the repay token to the wrapper** (`safeTransferFrom`), so approve the wrapper, not the mToken.
  It receives mTokens of the collateral and redeems them itself.
- **Flash source:** Morpho Blue on OP Mainnet is `0xce95afbb8ea029495c66020883f87aae8864af92` (FlashLoan topic
  matches, 89.9k USDC on 2026-11-17).

## Competition, 7 days to 2026-11-17 (blocks 159356037-159658437)

14 wrapper takes (82 USD repaid), all by wallet `0x5ac9bc14...` driven by EOA `0xd9fffdf0...`: 12 in the block
after the round (2 s), one after 2 blocks, one after 4; priority fee 0.0001-0.05 gwei. Largest: 25.90 USDC
repaid, +0.505 USDC, 1.32M gas (`0x9f141689...`). Class gross for the liquidator: about 1.5 USD in the week.
Data: `scratch/trial-moonwell-optimism/windows.json`. Bot: `trial-moonwell-optimism` (attempts:1702, 1705).

## Fork pitfall met here

Anything gated on `block.timestamp` needs pinned fork time. After `fork reset`, the first proof ran with fork
block timestamps past the 10 s delay, so the wrapper call "succeeded" on a borrower that was not takeable early
on mainnet. Pin `evm_setNextBlockTimestamp` (reset block time + 1 s per send) before every send and assert the
success block's timestamp is inside the window; cross-check with a relay `eth_call` at the historical block with
a code override (`scratch/trial-moonwell-optimism/proof.py`, `selftest.py`).
