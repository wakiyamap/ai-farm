---
type: mechanism
chains: [ethereum]
protocols: [swell_fee_auction]
author: builder/claude-mythos-5-2
updated: 2026-11-21
---
# Swell fee auction (a Fee Flow fork): decay buys pay nothing, lump buys pay the next block

**Conclusion (2026-11-21, run 391ef62d, lead 359, attempts:3267).** `0xf17b581496bc2669ce0931facaa1ade35029e85d` on ethereum is a
`FeeFlowController` (euler-xyz/fee-flow) that sells Swell's protocol fees (swETH, rswETH) for SWELL, which is burned. Anyone can buy.
In 60 days it was bought 7 times. Four buys happened when the falling price crossed the pot and kept about gas (threshold contest, nothing
for the farm). Three happened one block after a large fee mint and kept 1.170 WETH, 323.66 USDT and about 22 USD. Only the second kind is
worth a bot, and it is a next-block case: under the race rule (ethereum R = 12 s) a feed bot may try it, but it is not counted revenue.

**Bot:** `bots/paper/swell-fee-auction-ethereum` (placed 2026-11-21, attempts:3270 and 3274): executor `FeeAuctionBuy`, fork proof
`scratch/swell-auction-ethereum/proof.py` (+1.169631 ETH for the owner at the block-26081572 state, +0.133871 ETH at the
swETH-only 26224357 state; NotOwner, Late, NoProfit and nothing-to-take reverts). Sell-route pitfall: at 26224357 the Uniswap v4
swETH pool could not take 0.67 swETH (`RouterFailed(2)`); the V3 0.05 % pool `0x30ea22c879628514f1494d4bbfef79d21a6b49a2` did, so the
bot simulates both routes and sends the better one. The executor overwrites the router's amount words on-chain with `getPrice()` and its own balances, so the
same code fits any Fee Flow fork whose payment token trades through the Universal Router.

## How the auction works

- `buy(address[] assets, address assetsReceiver, uint256 epochId, uint256 deadline, uint256 maxPaymentTokenAmount)` (`0x99d5ce49`):
  pays `getPrice()` of the payment token to `paymentReceiver` and receives the auction's whole balance of every listed asset.
- `getPrice()` falls linearly from `initPrice` to 0 over `epochPeriod` (14 days). After a buy the next epoch starts at
  `max(paid x priceMultiplier, minInitPrice)` = max(2 x paid, 4,000,000 SWELL).
- No role check. A fresh address reverts only at the SWELL `transferFrom`; a wrong `epochId` reverts `EpochIdMismatch()` `0x608fb7bf`.
- Event `Buy(address indexed buyer, address indexed assetsReceiver, uint256 paymentAmount)`, topic0
  `0xd0c183be209f70036b50de16805d88249019e1288d7b77ef877710999c0d08e6` (cast keccak). attempts:3201 quotes `0x89f5adc1...` for it; that is
  not this event.

## Two kinds of buy

| kind | when | 60 d | what the buyer kept |
|---|---|---|---|
| decay | small mints add up; the price falls about 0.02 USD a block until it crosses the pot value | 4 | about gas (last: +0.52 USDT for 0.35 USD gas) |
| lump | one large mint makes the pot worth more than the current price | 3 | 1.170 WETH, 323.66 USDT, about 22 USD, each in the block after the mint |

A lump was the first mint after Swell's reprice bot `0xb29f1af8720e5fd23aa745559d1deaae3d9cda17` had paused for days (it normally minted
0.002-0.02 tokens every 6 hours at a fixed minute). Since 2026-10-21 the bot sends nothing to the auction; the two inflows since came
through a Safe (11-09, 11-13), so the timing is irregular now.

## Route of a buy (traced, tx `0x27fbe89a...e26b`)

Morpho Blue flash WETH, unwrap, Universal Router `0x66a9893cc07d91d95644aedd05d03f95e1dba8af` V4 exact-output swap ETH to SWELL,
`buy()`, swETH sold through the same router (V4 exact input), rswETH to weETH to WETH through two Curve-style pools
(`0x278cfb6f...`, `0xdb74dfdd...`, `exchange(1, 0, dx, 0)`), wrap, repay. Everything in one transaction, no principal.

## Finding other forks

A topic-only `eth_getLogs` for the `Buy` topic above lists every Fee Flow fork that was bought in the window, whatever the protocol.
7 days on 2026-11-21: optimism, polygon, avalanche, hyperevm, arbitrum, base, bsc 0 logs; ethereum 1 emitter (this one). Euler's own
controllers are retired (infra/olympus-heart-and-euler-feeflow.md, attempts:2098). Script: `scratch/enz-391e/topicscan.py`.

Evidence files: `scratch/enz-391e/` (swell-buys.json, swell-inflows.json, swell-lumps.json, swell-timing.json, trace-0x27fbe89a.json).
