# whype-gap-elysium

Holding-frame mean reversion on the days-old Elysium chain: pool A
`0x97796d80b6a1db78632f7451196b04f307329eb6` (UniV3-style, token0=USDC 6dp,
token1=WHYPE 18dp, `fee()` currently 1152 = 0.1152%, dynamic) prices WHYPE at a
**persistent median -0.86% discount** to the HyperCore reference (Hyperliquid HYPE
1m closes), measured over 26.5 h in attempt 1276. When the gap crosses **-1%** the
bot buys WHYPE with 20 USDC in that pool; it sells back **in the same pool** when
the gap closes past **-0.1%** (take), when the reference falls **5%** below the
entry reference (stop), or at **24 h** (frame timeout). Profit is realized in the
pool in USDC; the reference is only a signal — the entry line is calibrated to the
pool's own baseline, not to zero.

## Mechanism and evidence

- Measurement (attempt 1276, run 14ef1f66): 12 closed round trips at entry <= -1%
  / exit > -0.1% recorded as **+12.79% of size net of pool fees in 26.5 h** at
  100 USD. **Recomputation this session from the same saved series**
  (`scratch/14ef1f66/ely_series.json` + `hype_candles.json`, fee 0.1152%/leg,
  buy/sell at pool prices) reproduces 12 trips and a ~21 min median hold but
  totals **-5.86 USD per 100 USD**, not +12.79 — the recorded number did not
  reproduce and EV is NOT independently confirmed (table below). One choppy
  downtrend day sample (HYPE -5.7%, range 59.8-69.2); the paper run is the
  second sample before any promotion claim.

### Per-round-trip table (recomputed, 100 USD size, pool A prices, 0.1152%/leg)

| # | in (UTC) | out (UTC) | hold | buy | sell | net USD |
|---|---|---|---|---|---|---|
| 1 | 11-14 05:58 | 09:22 | 204 m | 68.61 | 68.75 | -0.03 |
| 2 | 09:32 | 15:15 | 343 m | 68.35 | 67.30 | -1.77 |
| 3 | 15:17 | 20:34 | 317 m | 67.18 | 64.04 | -4.89 |
| 4 | 20:46 | 20:55 | 8 m | 62.82 | 62.49 | -0.75 |
| 5 | 21:01 | 21:03 | 1 m | 62.24 | 62.42 | +0.06 |
| 6 | 21:04 | 21:15 | 11 m | 62.16 | 60.77 | -2.47 |
| 7 | 21:16 | 21:17 | 1 m | 60.07 | 60.98 | +1.28 |
| 8 | 21:21 | 22:08 | 47 m | 61.28 | 61.71 | +0.46 |
| 9 | 22:10 | 22:12 | 2 m | 61.36 | 61.74 | +0.38 |
| 10 | 22:15 | 22:15 | 1 m | 61.24 | 62.43 | +1.70 |
| 11 | 22:22 | 11-15 01:23 | 181 m | 62.89 | 62.97 | -0.11 |
| 12 | 01:30 | 02:02 | 31 m | 62.36 | 62.67 | +0.27 |

Sum -5.86 USD over the 26.5 h window (mean -0.49/trip); the three losses >= 1 USD
are all entries into the 67->64 leg of the downtrend — the strategy pays only
when the gap closes faster than the reference falls. Windows: 0.5%-gap episodes
151/26.5 h, median duration minutes (attempt 1276) — the 10 s poll is ~2 orders
of magnitude inside every window; entry and exit waits are the hold itself
(median 21 min), far under `holding_max_hours` 24.
- Race rule: episodes last minutes; the bot polls every 10 s (>= R = 3 s), entry
  is feed-free polling, counted per decision 2026-11-14-race-rule-seconds.
- Incumbent: router 0x9ee35bf1bd... (the EOA 0xabb2acd3 of lead 132) trades this
  pair but leaves the band open (only 2% of samples price within 0.1% of the
  reference).

## Worst loss (holding frame)

- Between buy and sell the executor holds <= 20 USD of WHYPE (the frame's whole
  risk budget here). The bot's own stop sells after a 5% reference fall: realized
  stop loss ~ -1.1 USD at 20 USD plus fees. Absolute worst case (nobody stops,
  WHYPE to zero): **-20 USD = holding_usd**.
- Per transaction: buy reverts unless the same-pool exit quote of the received
  WHYPE >= minExitUsdc (set at 99.5% of cost, so entry slippage <= 0.1 USD at 20
  USD); sell reverts below minUsdcOut (99.5% of the live quote); exitAll() has no
  minimum (frame exit for gate stop) — its worst case is fee + slippage on <= 20
  USD against 59.6k USDC depth: < 0.15%. Gas: Elysium ~0.5 gwei, < 0.01 USD/tx.

## Exit pool depth (frame rule >= 10x)

Pool A holds ~59,625 USDC + ~1,742 WHYPE (attempt 1276; re-read today: fee
1152, liquidity non-zero, price 64.23 USDC/WHYPE). 59.6k / 20 = ~3,000x.
Depth is not the binding risk; the -0.86% baseline drifting is.

## Executor and fork proof (re-run green 2026-11-15)

`executor.sol` (WhypeGap): buy(pool, usdcIn, minWhypeOut, minExitUsdc),
sell(pool, minUsdcOut), exitAll() (owner-only, no args, no revert when empty),
quoteExit(pool, whypeAmt) = post-buy sqrtP quote of the FULL received amount
minus fee (WhypeGap.sol:80-82 — the frame guard is the executable exit quote,
not a pre-trade spot check). No baked targets (pool is an argument; exitPool is
set by the last buy because the frame ABI needs a no-arg exitAll).

One script `scratch/whype-gap-elysium/proof.sh` (lease/reset/deploy/fund, then,
fork executor 0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352):
buy success `0xbf73b1b2af33…` (20 USDC -> 0.2986 WHYPE); GUARD_EXIT revert
`0x71de9c7dcb…` (minExit 19 USD on a 1 USD buy); sell success `0x5bceda91e6…`
(-> 19.9554 USDC, WHYPE zero); buy2 `0x0ef370c2…` + **exitAll WITH position**
`0x731834809d…` paid 39.91029 USDC to the wallet, executor left with 0 USDC,
0 WHYPE; exitAll empty no-revert `0x66efde11…`; stranger sell reverts `0x9e8bdac2…`
(NOT_BOT); USDC/WHYPE allowances both 0 at the end. (exitAll is time-independent;
the 24 h timeout is bot-side, so exitAll-with-position is the same proof.)

**Elysium pool A swap-hook facts (cost this session its root-cause hunt):**
pool A embeds a hook module (0xc0ed888afe…) that runs inside `swap()`.
(1) It STATICCALLs address `0x…64` — a chain-level sentinel (mainnet code `0xfe`)
returning a block-number-like word; a reset anvil lacks it, so forks need
`anvil_setCode 0x64 0x435f5260205ff3` or every swap reverts `invalid opcode`.
The earlier "direct pool.swap is router-gated for fresh contracts" (attempt
1281) was this fork artifact — the router itself calls the same pool `swap()`
(winner tx `0x59ea43af…`: Multicall3 -> router -> pool.swap directly).
(2) The hook reverts `"IG"` unless `gasleft() >= 250000` (slot 2 hi32) at its
afterSwap check: a sell with gasLimit 569k failed at 302,955 used (~258k left),
the same call with a 3M limit succeeded. Gas limits for this pool therefore get
estimate + 1M floor (bot.py `gas_limit_for`); on `fork send` the key is `gas`
(`gasLimit` is ignored and the node default ~571k reproduces the failure).

## Reads

slot0() via relay every 10 s = 8640 eth_call/day = ~26k CU/day ~= 0.014 USD;
Hyperliquid candleSnapshot once per 55 s (external API, no CU). EV >> read cost.

## State machine

one position at a time; state in `state/state.json` (holding, entry time/ref,
whype amount, round trips); every decision and heartbeat logged to
`logs/bot.jsonl` (machine-readable, gap + executor quote recorded).
