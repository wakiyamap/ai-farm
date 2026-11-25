trial

# trial-mintclub-hunt-base

Mint Club V2 bonding-curve tokens whose reserve token is HUNT (0x37f0c2915cecc7e977183b8543fc0864d03e064c): MT, DR, HEPE,
ONCHAT, SIGNET. The Bond 0xc5a076cad94176c2996B32d8466Be1cE757FAa27 mints and burns each of them against HUNT at the
curve's step price less a royalty (MT 0.3 pct, DR 1, HEPE 0.1, ONCHAT 1, SIGNET 0.3), open to anyone. Each token also
trades on a hookless Uniswap v4 native-ETH pool (fee 1 pct + 0.1 pct protocol fee), and so does HUNT (pool id
0xaa40332c..., 13.5e21 liquidity, about 0.88 ETH for a 1 pct move). When HUNT / ETH moves, or somebody trades one token
pool, the curve and the pools disagree:

- burn: WETH -> ETH -> token (v4), Bond.burn -> HUNT, HUNT -> ETH (v4)
- mint: WETH -> ETH -> HUNT (v4), Bond.mint -> token, token -> ETH (v4)

One transaction through the BondArbV4 executor, Morpho WETH flash loan, reverts unless WETH + ETH grew by minProfit, pays
native ETH to the bot wallet. Sibling of trial-mintclub-bond-base (hDRB); that bot's executor sells the reserve on a V3
pool, which does not exist with depth for HUNT (the HUNT / WETH V3 pool 0x9d744d3d holds 0.002 WETH), so this bot has
its own executor with both legs on v4.

## Competition, last 7 days (blocks 57476167-60500167, to 2026-11-21 19:46Z)

61 Bond mint / burn events on the five tokens (scratch/rc3f9/bondhist.py scan; scratch/rd313/mkroutes.py prints them).

| address | takes | notes |
|---|---|---|
| 0xf7c70a04d2c0bba340fffb1816d30a25dd3562f6 (EOA 0x3de7e4a0..) | 18 | same route as this bot; tx 0xccb1b4fb..., +0.0000781 ETH, 1.62M gas at 0.0074 gwei, tx index 19 |
| 0xb4008dc2ad60c9da12b2088e66fedd00a85ff135 | 16 | MT / DR mints, ONCHAT / SIGNET / HEPE burns |
| 0x7b804b6c94c22cdc8327e51300ebcd76779be92b (EOA 0xa35854d1..) | 5 | MT burns through the HUNT / MT v4 pool; tx 0xe2ba49e8..., +0.000049 ETH, 1.76M gas at 0.006 gwei, tx index 43 |
| 0x48682a623b2a686e905c8e801a925d9885fb30a0 | 3 | MT burns |
| 0x4d6823b083a7d03bce47d50e224903016353b6c8, 0x0000000000be226a.., 0x000000000093c087.., others | 19 | routers, exits and plain users |

- Blocks to take: bursts. First to last take of a burst: 57774585-57775369 (157 s; nine takes in the first 18 s),
  59997926-59998381 (91 s), 60041543-60042516 (195 s), 60062403-60063684 (256 s). The first takes land within seconds
  of the trigger; later takes on the other tokens follow over minutes.
- Priority fee: none seen (gas price 0.005-0.0075 gwei = base fee, tx index 2-201).
- What this bot's route would have found at the parent block of each event (scratch/trial-mintclub-hunt-base/windows.py,
  windows.json: the bot's screen, size and exact run() as an eth_call): profitable at 39 of 61 parents, 36 above
  0.00002 ETH. Typical 0.00003-0.0004 ETH; the DR burst of blocks 57774585-57781494 0.0018-0.016 ETH a parent
  (overlapping: each take shrinks the next).

## How it runs

Timer bot, POLL = 30 s. One Multicall3 eth_call a look: PoolManager.extsload of each token pool's slot0 and of the HUNT
pool's slot0, Bond.priceForNextMint per token. A route whose marginal round trip is above 0.2 pct after all fees is
sized by simulating the exact run() at 0.002-0.08 ETH. It sends only when the simulated gross > 1.3 x the send's gas
cap (gas limit x max fee + L1 allowance), with minProfit = that cap, so an included send pays for itself or reverts.
Priority fee at most 1/10 of gross, never above 0.1 gwei. `send_result` lines carry won / lost, gas used and the
winner's block.

Live: executor address from `EXECUTOR_ADDR_BASE` / `EXECUTOR_ADDR` (exits if unset), logged in the `start` line.
Paper: code override `executor-runtime.hex` (eth_getCode of the fork deployment of proof.py).

## Read cost

30 s x 1 eth_call (26 CU) = 74,880 CU/day, plus about 5-8 calls per candidate seen (sizing, block, estimate, guard);
identical prices are not re-simulated. Budget 80,000 CU/day = 0.042 USD at 1M CU = 0.53 USD; hard cap in code
95,000 CU/day (sleeps to 00:00 UTC). No feed filter (the triggers are v4 PoolManager Swap events, a busy emitter).

## Proof

scratch/trial-mintclub-hunt-base/proof.py -> proof-result.json. Burn at parent 60062500: +77786197664234 wei (ONCHAT,
0.01 ETH), success 0xa9719957bc96e7d8c8ce212ac4d1130bb6f6840dbb3011223a54f740f2501426. Mint at parent 57774584:
+2784146425442347 wei (DR, 0.01 ETH), success 0xb310d958261779a5cb5d5579071fde9a8c4b5c47708f9748ee8971cfcd0be2a4.
NotOwner, NoProfit guard, repeat and opposite-direction reverts in both; no leftovers.

## Known limits

- Gas is 0.75-1.9M a take (the Bond walks its step array), so the send line is about 0.00001-0.00003 ETH at today's
  base fee; smaller gaps are logged as `gross_below_send_line`.
- MT also trades on a HUNT / MT v4 pool (0x7b804b6c's route) and many hooked pools; this bot only uses the native-ETH
  pools, so it misses gaps that exist only against those.
- Mint sizing uses the marginal curve price; when a mint crosses a step the Bond reverts (0x07728bb0) and the bot
  keeps the largest size that worked.
