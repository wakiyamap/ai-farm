# trial: trial-cv3-buy-polygon

**Trial bot** (decision 2026-11-17-cheap-chain-trials): cheap chain, race rule and EV floor
waived, the win rate is measured live by sending. Polygon copy of `trial-cv3-buy-optimism`
(same author, same executor design, own copy of everything). Built from lead 236.

After anyone absorbs an underwater account on Compound v3 Polygon (cUSDCv3
0xF25212E676D1F7F89Cd72fFEe66158f541246445, base USDC.e 0x2791bca1..4174; address from
compound-finance/comet `deployments/polygon/usdc/roots.json`, `baseToken()` read), the
collateral sits in the comet's reserves and anyone may `buyCollateral()` it at the comet's
discount. The executor `Cv3FlashBuyOut` does it with no principal, in one transaction:
flash-swap on a UniV3 {collateral, USDC.e} pool (sell exactly the quoted collateral), pay the
comet from the pool's USDC.e inside the callback, sell the USDC.e surplus for native USDC
(0x3c499c54..3359, the USDC the farm counts on polygon) on the UniV3 USDC.e/USDC 0.01 % pool
0xd36ec33c..a418, revert unless the USDC surplus exceeds `minProfit`, send the USDC to the bot
wallet.

## Competition, last 7 days (eth_getLogs, blocks 97,060,731-97,463,919, `scratch/cv3x/scan.json`)

- 4 absorb txs (blocks 97,332,763 / 97,332,778 / 97,333,535 / 97,334,218, all within 50 min);
  13 BuyCollateral, 4 inside the absorb tx; 9 residue buys by 6 buyers, one of them dust.
  cUSDTv3 0xaeB31836..9a07 had no event in 7 d and is not covered.
- The 8 non-dust residue buys (receipts in `scratch/trial-cv3-buy-polygon/discover.json`;
  POL ~0.0755 USD, base fee ~250 gwei):

| buy tx | block | blocks after absorb | executor | paid (USDC.e) | kept (gross) | gas used | priority fee | cost |
|---|---|---|---|---|---|---|---|---|
| 0x4be4f088..25b3 | 97,332,764 | 1, idx 0 | 0x10e3c6c0 | 2930.25 (WETH) | 124.26 USDC.e | 749,834 | 286,278 gwei | 214.9 POL (~16 USD) |
| 0x6aa6a3d3..19d2 | 97,332,764 | 1, idx 110 | 0xa0000470 | 193.47 (WPOL) | 156.8 WPOL (~11.8 USD) | 626,468 | 35 gwei | 0.18 POL |
| 0xbd72d73b..8820 | 97,332,765 | 2, idx 1 | 0x8f33bea7 | 24.69 (MaticX) | 2.67 USDC.e | 600,005 | 4,277 gwei | 2.72 POL (~0.21 USD) |
| 0x7d66bc80..c836 | 97,332,779 | 1, idx 0 | 0xb2407d89 | 62.11 (WBTC) | 6,168 sat (~3.6 USD) | 861,917 | 30,654 gwei | 26.6 POL (~2.0 USD) |
| 0xf0f047b3..5130 | 97,333,536 | 1, idx 0 | 0x10e3c6c0 | 248.56 (WETH) | 10.63 USDC.e | 541,575 | 27,021 gwei | 14.8 POL (~1.1 USD) |
| 0xf1d86d6a..d2ff | 97,334,218 | 0 (idx 61 -> 138) | 0x30a9f049 | 1899.69 (WBTC) | 845 WPOL (~64 USD) | 718,548 | 120 gwei | 0.27 POL |
| 0x5828395d..8e33 | 97,334,219 | 1, idx 0 | 0x10e3c6c0 | 23,155.48 (WBTC) | 1131.2 USDC | 612,219 | 2,637,034 gwei | 1614.6 POL (~122 USD) |
| 0xe8559480..65e2 | 97,334,220 | 2, idx 0 | 0x10e3c6c0 | 4930.36 (WETH) | 174.30 USDT | 909,352 | 266,754 gwei | 242.8 POL (~18 USD) |

- Blocks to take: 0-2 (0-3 s). Priority fee level: two tiers. 0x10e3c6c0 (sender 0xb0fe6e9c)
  bids 10-13 % of gross and takes tx index 0; the others won at 35-30,654 gwei.
- This bot wakes on the feed after the absorb block and lands one or two blocks later at best,
  bidding up to 25 % of gross but never more than the per-send cap of 0.95 USD (about
  9,700 gwei at a 1M gas limit). It cannot outbid 0x10e3c6c0 on any lot whose gross is above
  ~8 USD; it can outbid the 35 / 120 / 4,277 gwei buyers when it lands in the same block, and it
  takes what 0x10e3c6c0 is late for or leaves (MaticX and stMATIC are not routed here). The
  expected share is small and is what the trial measures.

## Fork proof (`scratch/trial-cv3-buy-polygon/proof.py`, polygon fork gen 2-3, output `proof.out`)

One script: lease, reset, deploy with constructor arg = owner, checks, release.

Case A, reset 97,332,763 (the absorb block of 0xb81c2391, parent of table rows 1-2):

- DEPLOY 0xcd483ceb1c552bb9dd3743e70c7428517484d623f40645066cbe539e32b826dc gas 950,161
- NON-OWNER 0xb0440e5bc0d1ccd7a911d9fd1fcb19bf4636fe9179ae6e950126a28fd5fc2d0e status 0
- GUARD (minProfit 1e12) 0x3c90de5479f96ef63d07f1f999c54cf6f32ad91a32754e6622d8a3ddea236449
  status 0, NoProfit (0x31708d59), owner USDC delta 0
- SUCCESS WETH via UniV3 USDC.e/WETH 0.05 % 0x45dda9cb..0608 + out pool:
  0x28ae9a985c31a3240a2858b6c9429b129098f356ffa2cd28aa74195d6edbd302 status 1, gas 664,191,
  block 97,332,767 (reset + deploy + two reverted checks): paid 2915.598478 USDC.e for the WETH
  residue, **owner wallet +102.954515 USDC** (= the eth_call simulation). Executor afterwards:
  0 USDC, 0 USDC.e, 0 WETH, 0 native, allowance to the comet 0.
- NOTHING-LEFT (same call again) 0x8b299ced2d314885507d2862301f20d0bfde471fe1ed9d1df7cfaf7f96e8b5fb
  status 0, owner USDC delta 0.
- SUCCESS WPOL via UniV3 WPOL/USDC.e 0.05 % 0xa3740945..6d32:
  0xc64421e30263b3406e01876ff2bf789b8f28c0753e7dc560f77aaab5c9113e46 gas 392,252,
  **owner wallet +11.697405 USDC**; NOTHING-LEFT 0xd148ab83ca5b3100a89690c34852dda0366f9061ce8c4c2b6c386b9c1ade7745 status 0.

Case B, reset 97,334,218 (absorb block of 0x1e2c7dbc, parent of table rows 7-8):

- WBTC lot of 23,165.68 USDC.e via UniV3 WBTC/USDC.e 0.05 % 0xeef1a950..03c8: the 99.5 % buy
  reverts in simulation (lot too big for the pool), the 50 % rung succeeds:
  0xfd9e3032220f0a056069205a9fe0380e833f2d4a4f239c4601aad3bfdf6253f8 gas 1,421,817,
  **owner wallet +128.178912 USDC**; NOTHING-LEFT 0x12588afaf52474ecb3c026099ff6d1db72ae0ec627e83864a524d9372dbf1707 status 0.
- WETH 3.0 lot: 0xfa37fb134b4697cbb5fec4cd4a9fc3c0d8386f4ae231c313dc5dbc0a8d64dccf gas 956,245,
  **owner wallet +139.121373 USDC**; NOTHING-LEFT 0x8236803cc9869911e77b2f862bd1477f3618c98e3d052a036a89f7341f864b5d status 0.

`scratch/trial-cv3-buy-polygon/paper_selftest.py` runs this bot's own `check()` on the fork at
97,332,763: the Multicall scan finds 2930.25 USD of WETH and 193.57 USD of WPOL, simulated
gross 102.954515 and 11.697407 USDC, gas limits 976,599 and 631,378 (estimate x 1.25), gas cap
0.95 USD each, `paper_sim` success twice (`selftest.out`).

Paper mode simulates the exact call with `eth_call` and a code override (the fork runtime,
`executor-runtime.hex`) at the fork address 0xfe00ddfe..8e9a (no code on mainnet), from the
owner baked into that runtime (0xc0ffee..02). Live mode uses the signer's address and
`EXECUTOR_ADDR`.

## What the bot waits for

- Feed `/logs/polygon`, address = the comet, topic0 = AbsorbCollateral
  `0x9850ab1af75177e4a9201c65a2cf7976d5d28e40ef63494b44366f86b2f9412e` (4 absorb txs / 7 d, bursty).
- On `gap`, `removed`, HTTP 429 / 503 / 400 or a connection error: re-read the reserves
  through the relay (at most once a minute while the feed is down), then continue.
- Safety poll of the reserves every 10 min (one Multicall3 `eth_call` for all routes).
- Routes: WETH, WBTC, WPOL, each with the UniV3 0.05 % and 0.3 % {collateral, USDC.e} pools
  (factory 0x1f98431c..f984 `getPool` results with their depth read on 2026-11-17,
  `discover.py`); the best simulated pool is used; a lot too big for the pool is retried at
  50 % and 20 %. MaticX and stMATIC have no direct USDC.e pool with liquidity and are not tried.

## Send rule and loss bound

Send only when the simulated USDC surplus is above that send's gas cap:
`gasLimit x maxFeePerGas x POL price`, with `gasLimit = eth_estimateGas x 1.25` (refused above
2,000,000), `maxFeePerGas = min(fee cap, 2 x gas price + priority)`, priority = at most 25 % of
gross and at least 30 gwei (polygon's minimum tip), and the fee cap chosen so the whole
expression never exceeds 0.95 USD. The POL price is max(0.10 USD, 1.15 x the price the comet
itself quotes WPOL at), re-read at every check (POL is ~0.076 USD today). `minProfit` in the
call is that cap, so a mined transaction either nets more than its gas cap or reverts
(`Cv3FlashBuyOut.sol` NoProfit check). Worst case per send = gas. Polygon is not an OP Stack
chain: `maxFeePerGas x gasLimit` bounds the whole cost. Every send logs `send_result` with
won / lost, gas used, gas cost, the winner's block and how many blocks after it we landed.

## Reads

Safety poll: 144 Multicall `eth_call`/day x 26 CU = 3.7k CU. Absorb wakes: ~0.6/day x (1 scan +
up to 6 sims + estimate + gasPrice) = under 1k CU. Feed: ~4 CU/min subscription = 5.8k CU plus
~35 CU per event. Total ~10k CU/day = 0.005 USD/day at 0.53 USD per 1M CU; the bot stops
reading at 60k relay CU/day (`CU_CAP`).
