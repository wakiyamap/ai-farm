One-shot (単発): take the untaken Bundles.fi v2 index rebalance on ethereum, then idle.

## What it takes

A Bundles Index (`0xe202345c1a32a98f894f02d077af98108376ade3` BUN / WBTC / USDC / WETH, `0xd19d6750760a8f41fc376c81526fcd8b38ab0d5a`
BUN / WBTC / PAXG / wstETH / USDC) is a weighted pool that reads no oracle. Its only way to trade is the public
`rebalance(tokenOut, amountOut, tokenIn, to, data)`: it approves `tokenOut` to `to`, calls `to.execute(data)`, then requires

- the weighted invariant of the two tokens not to fall (`_ensureReserves`), and
- a fee in BUN of at least `dIn / balIn x balBUN x wIn x swapFee / (wBUN x (1000 + swapFee))`.

`swapFee` is 273 and 222 (static), i.e. 21.4 % / 18.2 % of the trade at the index's internal BUN price, about 19 % at the
market BUN price (Uniswap V2 pair `0x25ad147b`, 0.0458 USD). So a take pays only when the index's price is about 24 % away
from the market. On 2026-11-20 ETH fell from about 1,760 to 1,617 USD; the first index still prices WETH at 2,243 USDC.

One transaction through the executor: pull USDC from the index, buy the WETH it must receive and the BUN fee with part of
it, pay the index, keep the rest as USDC, revert unless that is at least `minProfit`. No principal.

## Why it is still there

One regular taker in 30 days (EOA `0xee5f1096…`, 15 takes, the last on 2026-11-14 at block 26,416,459; three other
senders once each, the last at block 26,385,756), no oracle in the index, and
a 19 % fee that hides the gap from generic arbitrage bots (the fee must be paid in a token with 30k USD of liquidity). The
gap opened today with the ETH fall: modelled profit of the best leg 0.3 USD at 09:43Z, 16.8 at 15:45Z, 29.7 at 18:46Z,
40.4 at 20:47Z, 45.0 at 21:17Z, 31.4 at 21:47Z (`scratch/oneshot-bundles-rebalance-ethereum/window.json`). Nothing is
paused or restricted: the fork success below is the real call.

## Net figure

Fork at head (reset 26,459,082): owner +33.67 USDC for 377,477 gas. Deploy 1,457,176 gas x 0.78 gwei = 1.84 USD, run
0.5-0.9 USD, sweep 0.1 USD: **net about 30.8 USD**. It shrinks if ETH recovers (about 1,720 USD closes it) and grows if
ETH falls. The bot sends only when simulated profit minus that send's gas cap is 10 USD or more.

## Private send

`send_route: private`: the incumbent's callback router is open to anyone, so a public transaction of this size could be
copied from the mempool; a private one that would revert is also not included. Deadline = head + 3 blocks;
`send_result` logs `private_not_included` when no receipt arrives by then, and the next poll tries again (at most 20 sends).

## Limits in code

- executor: `NoProfit` unless USDC left >= `minProfit` (70 % of the simulation, never under the gas cap); `Expired` after the deadline block; owner only.
- gas limit <= 1,500,000, `maxFeePerGas` <= 15 gwei (worst case 0.0225 ETH = 36 USD; typical 490k x 2.1 gwei = 1.7 USD).
- at most 6 wins and 20 sends, then `idle` rows only.

## Read cost

144 polls a day x 26 `eth_call` x 26 CU = 97,300 CU, plus about 100 CU per evaluated candidate: about 110,000 CU/day =
0.06 USD at 0.53 USD per 1M CU. Hard cap 150,000 CU/day in code. No feed filter.

## Logs (`logs/bot.jsonl`)

`start` (executor=…), `poll` (best candidate and its modelled profit), `opportunity` (exact-bytes simulation, gas cap),
`paper_sim` (paper), `send_result` won / lost / private_not_included with gas used (live), `opportunity_skip`,
`simulate_revert`, `idle`.

## When it is done

After the take, or when another sender's `Rebalanced` log shows it is gone, write `inbox/meta/` (bot id, tx hash) so
the stop can be requested. The recurring version of this (every later 24 % drift) is lead 336's follow-up.
