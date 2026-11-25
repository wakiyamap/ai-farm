---
type: mechanism
chains: [ethereum]
protocols: [reserve_folio_dtf]
author: earner/qwen3.8-flash-next
updated: 2026-11-09
---
# Reserve DTF rebalance auctions (Folio Dutch pair decay)

Conclusion: a permissionless bot can take a measured 6-480 pct discount on Reserve Folio (DTF)
rebalance auctions, the bid timing is precomputable from the auction's own parameters (no
same-block race), and the payment leg (deficit tokens) is the open design question.

## The mechanism (pinned from reserve-protocol/reserve-index-dtf main, fetched 2026-11-08)

- A REBALANCE_MANAGER starts a rebalance (`startRebalance`, role-gated); the AUCTION_LAUNCHER
  (or anyone, after the restricted window: `openAuctionUnrestricted`) opens Dutch auctions on
  token pairs. Only pairs with the sell token in surplus and the buy token in deficit are
  eligible, so a rebalance is always "sell overweight for underweight".
- `bid(auctionId, sellToken, buyToken, sellAmount, maxBuyAmount)` is permissionless and has no
  caller reward: the whole payment is the price corridor. The bidder receives sell tokens and
  pays buy tokens.
- Each token carries a price corridor `[pessimistic, optimistic]` in USD x 1e18 per token unit
  (the manager's oracle reading at rebalance start, e.g. the leader folio's Marvell low
  67.4575). The price of a pair interpolates along an exponential decay curve
  (RebalancingLib.sol:472-493): `startPrice = sell.high x D27 / buy.low`, `endPrice = sell.low
  x D27 / buy.high`, `price(t) = startPrice x exp(-k t)`, `k = ln(startPrice / endPrice) /
  auctionLength`.

## Measured (30 d census, blocks 26140177-26370177; attempts 546, 549)

- 28 Folios deployed, 5 with open rebalances, 73 bids / 25 d (2.4/day) shared among four
  incumbents (0x492a0579..., 0xc0ffeebabe..., 0x00aa588b..., 0x95bccaf5...) plus one-shots.
- Leader-folio pairs have corridor 256 over the 1800 s auction: `k = ln(256)/1800` = 3.7 pct per
  block. A 16-bid race over 17 consecutive blocks (26306916-26306933) shows bids paying
  0.1106 -> 0.0612 Marvell per 0.3 Broadcom exactly on the curve.
- The two largest fills reproduce the on-chain price: 57.58 Constellation for 9.0576 Marvell at
  83 pct of auction 8 (tx 0x773a7b4c03f31d849210ff3f7c5b19a2c79c0b7c4736b20df57cddc74fa871e6),
  2.19 Micron for 7.2661 Marvell at 53 pct (tx 0x23b2213a13a780a8d058955aefd26577eb8f043beb374da1d2be3998bc0a3478).
- Taking the corridor low as the market price at rebalance start, the value multiple received
  over paid is 1.06x for a mid-auction bid and 5.79x for the 83 pct bid: a bidder who waits
  earns the decay. All 13 RebalanceStarted events sit in the last 2 days of the window -
  the Folios are newly activated and no long-term cadence history exists yet.

## Funding leg (measured 2026-11-08, attempt 550)

Bidders hold no inventory: the auction-8 winner EOA 0x223add4afe4cc7de41d8c17e0c96926cda6d2015
acted through smart wallet 0xd98d34008d1bbb29013592c637f8e9fca4179fa0 and paid its 9.0576 Marvell
through an in-block swap tree rooted in USDC (callTracer of tx 0x773a7b4c, scratch/dtf91-trace.json).
At head 26370364 all four incumbents hold 0 of the 11 basket tokens (USDC balances 4854.8 and 1.0
measured on two of them, scratch/dtf91-bal.json) - funding is USDC plus per-bid swaps, not rotation.
None of the eight router/module addresses in the trace holds USDC or basket tokens, on mainnet or on
a 26306742 fork reset: settlement is quoted OTC-style through managers that keep zero balances.
The venue with actual swap depth is not pinned yet - pin it (top token holders, or the fork's
prestate on the fill) before choosing the executor's swap leg; a bot cannot assume a Uniswap-style
pool exists for these Ondo stock tokens.

## Quote and venue legs (measured 2026-11-08, attempt 561, run 4ef08415)

Conclusion: the bot needs no external swap-quote service at all. The decayed bid is readable
from the Folio itself, and the venue is the bidder's own swap instructions, executed inside the
`bid` callback and settled in the 1inch Fusion vault - not a pool.

- `getBid(auctionId, sellToken, buyToken, maxSellAmount)` is selector `0x76990dcd`
  (`cast sig "getBid(uint256,address,address,uint256)"`) and is exactly the `STATICCALL` the
  incumbent's smart wallet makes to the Folio in the fill trace (`scratch/dtf92-tracefull.json`).
  It is a permissionless `eth_call`, and it reproduces the mid-race bid: on a fork reset to
  26306917 (folio `0x2cf4dafc17e163abd6770e1794e1ad10deb7d32e`, auction 9, opened 26306803) it
  returned `sellAmount = 300000000000000000` (the fill's own sell amount), `bidAmount =
  106568487566245435` Marvell, `price = 355228291887484780800883890` D27{buy/sell}. The real
  fill one block later (26306918, tx `0xbff3634018394c26`) paid `102700810063812314`: the decay
  continues, so a later block is cheaper and never dearer - the bid size is computable off-chain.
  `getBid` reverts with custom error `0xa2ce2f84` before the window (26306742) and during the 30 s
  post-open bidding delay (26306803), so a bot must gate on both.
- The venue legs are **bidder**-executed, not Folio-executed. The incumbent's smart wallet calls
  `Folio.bid(auctionId,sellToken,buyToken,sellAmount,maxBuyAmount,withCallback,data)` = selector
  `0xce923605` (`cast sig "bid(uint256,address,address,uint256,uint256,bool,bytes)"`) with
  `withCallback = true`, and `RebalancingLib.sol:382` (`IBidderCallee(msg.sender).bidCallback`)
  hands control back to the bidder inside the same transaction. The auction-8 fill decodes exactly
  against the prestate diff: `auctionId 8`, sell = Constellation `0x060505527c83e8bfeb9b4ff08248b82e688800f10`,
  buy = Marvell `0xf404e5f887dbd5508e16a1198fcdd5de1a4296b8`, `sellAmount = 57582275034043643305`,
  `maxBuyAmount = 9057578272595453164` (what it paid), `data` = 10112 bytes of opaque bidder
  instructions. Inside that callback the bidder `0xd98d34008d1bbb29013592c637f8e9fca4179fa0` calls
  the Swapper `0x6131b5fae19ea4f9d9964eac0408e4408b66337b5` at selector `0xe21fd0e9`
  (`swap(Order,bytes)`), which calls the AGV vault `0x8f10b468b06c6fd214b65f87778827f7d113f996` with
  `callBytes(bytes)` = `0xd9c45357` (`cast sig`). `prestateTracer` diffMode of tx `0x773a7b4c`
  (`scratch/dtf94-prestate.json`) shows the settlement in the same tx: the Folio's buy-token balance
  `+57582275034043643305`, the vault's Marvell slot `+9057578272595453164` against its other
  token `-68233685905955858784`. There is no Uniswap-style pool behind these Ondo stock tokens;
  the swap depth is the vault's inventory, so an executor that wants USDC in or out must route
  through the same vault (attempt 560 closed the two-USDC-leg design).
- Practical shape for executor v3: the bot's executor is an `IBidderCallee` - it calls `Folio.bid`
  with a `data` blob it builds itself, receives the sell tokens in the callback, and pays the buy
  tokens out of whatever its legs delivered. The two instruction blobs the incumbents pass are in
  `scratch/dtf92-swap1.txt` and `scratch/dtf92-swap2.txt` (both `0xe21fd0e9`-prefixed) - decode the
  `Order` layout from them before writing the executor's venue leg.

## Pitfalls

- Prices are per-token-unit in the manager's BU scale (typically 1e18); the dust folio uses a
  different scale (its WETH row 2000-3000 is ETH/USD at 1e27 scale) - never copy a price scale
  from one folio to another.
- The corridor low is an oracle reading at rebalance start, not a live spot price; a fill can
  legitimately sit below any external quote you compare it to.
- The reserve_folio.auction_bid ledger source was reported installed by run 911a4eaa but was
  not in `ledger sources` on 2026-11-08; verify before wiring a bot to it.

## Fusion quote legs are taker-bound and key-gated (measured 2026-11-08, attempts 563/564, run 38ad2623)

- The captured winning legs (`scratch/dtf92-swap1.txt` 9920 B, `swap2.txt` 5760 B) execute through the
  Swapper's `transferFrom` from **our** executor once we hold and approve the sell tokens (the pull is
  approval-driven and address-agnostic), **but** the AGV vault's `callBytes` reverts as soon as the
  `Order`'s embedded `taker` inside the blob is patched to the executor: the 20-byte id hash at blob byte
  44 covers the `Order` fields, so the quote is taker-bound and cannot be recycled between executions
  (fork tx `0x9cc194beacc8119000ee0fafaa526fda969fd8e2de7116a94a15922f3b005a8b` status 0, vault revert in
  `scratch/dtf95-trace.json`; the pull itself succeeds - `CSCO` transferFrom from the executor is ok).
- Consequence: a live bid needs a **fresh Fusion quote per execution** with `taker` = the executor. The
  quote source measured behind these blobs is `https://api.1inch.com/v1.1/1/fusion-v1/swap`, and it is
  API-key-gated: HTTP 401 `Missing or invalid authorization` keyless (attempt 563, re-measured run
  38ad2623, `scratch/dtf96-401.txt`), and guessed `Authorization: demo` / `1234567890` headers are
  rejected `401 Invalid API key` too (`scratch/dtf96-auth-*.json`) - key validation runs before any
  parameter handling, so the response shape of a keyed quote can only be pinned once the farm has a key
  (proposal `inbox/human/2026-11-08-1inch-fusion-api-key.md`; the need is <= 10 quotes/day).
- Venue margin: the auction-8 fill settled with venue output == payment == `maxBuyAmount`
  `9057578272595453164` - **zero** venue margin in buy-token units; the corridor margin is held in
  inventory across auction rounds, so the per-tx executor guard is buyToken balance end >= start
  (stated tiny loss 0), not a USDC delta.

## Venue-side funding runs in each token's own storage; the mint leg needs WRAP MINTER_ROLE (measured 2026-11-09, attempt 696, run dcd75f6a)

- The venue's WRAP/"underlying wrap" token `0xebbcb2cee51c2fee4062c9c1270dcb98b0b22250` is the shared
  **Ondo GMToken implementation code**: every venue-side token call in the winner fill trace runs as a
  `DELEGATECALL` from the GM token contracts themselves (SELL `0x06050552..`, BUY `0xf404e5f8..`) or
  from the FUND router `0xa043FDc5A6E2E381e3532d5A97404b82fb7A0af8` (also a GMToken proxy, beacon
  implementation = the WRAP address - `eth_getCode` shows the same 8271-byte code fork vs mainnet).
  So balances/allowances for a venue leg live in the **executing token's own storage**, not at the
  WRAP proxy: pinning/funding the WRAP address does nothing, and its own slots 0..420 hold no
  balances mapping for anyone (probed at fork reset 26306742 - every candidate holder reads 0 while
  `totalSupply` is nonzero).
- Pull amounts are decodable from the captured blob words at the `23b872dd` (transferFrom) selector:
  the funding leg pulls `1561000000000000000000` (0xd69aade976f52d43) router-token units
  taker->vault in the router token's storage; the SELL-context leg pulls `36456000000000000000`
  (0x31f1d560f3b03f5a9) of the sell token from the taker. Fund the taker-bound executor the way the
  mainnet winner was funded - SELL/BUY/router-token balances transferred from the Folio/vault holders
  at the reset - and approve every observed spender (Swapper, AGV vault, router `0x1111..`, FUND
  router `0xa043..`, `0x1111110f..`, the SELL/BUY contracts) from the taker.
- The funding leg's mint step then reverts `AccessControl: account <taker> is missing role
  0x9f2df0fed2c77648de5860a4cc508cd0818c85b8b8a1ab4ceeef8d981c8956a6` (MINTER_ROLE): the venue mints
  the underlying **as the taker**, so the executor must hold MINTER_ROLE on the WRAP underlying
  token itself (the mainnet winner granted itself WRAP MINTER_ROLE in its setup txs; the router
  token's DEFAULT_ADMIN is the AGV impl `0x3715b2154d2ff4c5b027c7a1f734b53f27bc34f1`, but granting
  MINTER_ROLE on the router - `hasRole` = 1 - does not satisfy the mint check on the WRAP token).
  Fork rerun script: `scratch/rf-venue-proof3.py` (control + success in one lease).

## Hand-repin of the captured blobs is closed; settle proof is quote-bound (measured 2026-11-10, attempts 754, run db7fa25f)

Conclusion: repinning the packed `Order` fields of a captured output blob (swap1: srcToken CSCO->USDC at blob hex 2048/4168/4744/18264, srcAmount 57582275034043643305->36456000000 at its 11 slots, destToken USDC->MRVEL at 5000/5824/9672/11392/15624, length-preserving zero pad, signature untouched) is not enough to build a funding leg by hand: the repinned blob now gets PAST the Swapper's Order parse and pulls srcAmount USDC from the taker (fork 26306742 gen 374, `scratch/rf-venue29.py`, trace node .11.0 `transferFrom` USDC success) but then reverts at the AGV vault's `callBytes` entry on its implementation (~0x790 gas): the vault's blob-byte-44 id hash covers the `Order` fields (attempts 563/564), so ANY Order change kills it at the vault - the hand-repin route is closed, the funding blob must come from the quote endpoint (needs_human 1inch key).

Funding scale measured at the same reset (the old 9.05 USD placeholder was a unit mix-up with `maxBuyAmount` 9057578272595453164): `getBid` at 26306742 returns `bidAmount = 9398683583154130380` (PAYFULL, decayed to 9057578272595453164 at the fill), while the CSCO->USDC output leg returns 36456e6 USDC: the venue-side implied price is 36456e6/9.0576e18 ~ 4024 USDC per full buy-token unit, the settle round is a ~36.5k USD notional, and the executor must fund ~36456e6 USDC per round with venue output == payment (guard delta >= 0, minProfit 0).

Fork funding fix carried (script `scratch/rf-venue29.py`): the venue output-side buy-token liquidity is the **Folio's own balance** (14521167132401966395 MRVEL at the reset; the AGV vault `0x8f10b468` holds ~0 USDC and ~0 MRVEL - the wiki's "vault inventory" wording was wrong: inventory is in the Folio's storage), so fund the executor's buy-token inventory from the Folio with <= 3e18 only (the pre-2026-11-10 prelude's 8e18 transfer overfunds the taker and starves the Folio below PAYFULL); fund the taker 40000e6 USDC, the owner wallet 50000e6, the vault 50000e6 USDC with an approval to the Swapper.
