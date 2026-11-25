# trial: trial-cv3-buy-base

**Trial bot** (decision 2026-11-17-cheap-chain-trials): cheap chain, race rule and EV floor
waived, the win rate is measured live by sending.

After anyone absorbs an underwater account on cUSDCv3 Base
(0xb125e6687d4313864e53df431d5425969c15eb2f), the collateral sits in the comet's reserves and
anyone may `buyCollateral()` it at the comet's discount. The executor `Cv3FlashBuy` does it
with no principal, in one transaction: flash-swap on a UniV3 {collateral, USDC} pool (sell
exactly the quoted collateral), pay the comet from the pool's USDC inside the callback, revert
unless the USDC surplus exceeds `minProfit`, send the surplus to the bot wallet.

## Competition, last 7 days (ledger compound_v3 base, blocks 55,406,213-58,369,752)

- 199 AbsorbCollateral events in 135 txs by 5 absorbers; 147 BuyCollateral by 8 buyers.
- 135 of the 147 buys are in the SAME transaction as the absorb (atomic, nothing left over).
- 12 buys had no absorb in their own tx (the residue class this bot tries), 5 buyers:
  0x8407699e (4), 0xb091bc76 (4, dust of 0.000001-0.0009 USDC), 0x860a7a04 (2), 0x5ac9bc14 (1),
  0xf000042d (1).
- Blocks from residue to buy (scratch/trial-cv3-buy-base/find_residue.py, reserves read at
  parent blocks): the copied case, cbBTC 90,882 sat absorbed at block 57,502,604 (tx 0x8c30d087..)
  and bought at 57,502,607 (tx 0x2c0433b40949afade98aeca585511020e9faea320625ae05192aad0f3660a317,
  56.82 USDC paid) = 3 blocks = 0.6 s. Two more real ones (8.37 and 0.57 USDC) were in reserve
  at parent but not 5 blocks earlier (1-4 blocks). Dust lots (0.1-0.16 USDC and below) sat
  for 15+ blocks.
- Priority fee: the winner of the copied case paid an effective 0.52 gwei on 341,808 gas
  (~0.33 USD at ETH 1,830) for ~1.5-2 USD gross. This bot bids at most 25 % of gross
  (0.185 gwei on that case), so it expects to lose such a contest unless the incumbent is late.

## Fork proof (scratch/trial-cv3-buy-base/proof3.py, base fork gen 1153, reset 57,502,606)

One script: lease, reset, deploy with constructor arg = owner, checks, release.

- DEPLOY 0xe59f4d62fec5e873fdcb6118047aa25cebae7280726695b8d874691ac248a51a gas 725,692
- NON-OWNER 0x1f15515d0e42ccd80bdd9a98d5f064ce52dccf4e4859fdf95fa9e09e6ae65ab8 status 0
- GUARD (minProfit 1e12) 0x543b197968fe13c520b798eda5292aff2e605cd7535f240d9d30db0c0066aa68
  status 0, NoProfit, gas 400,928, owner USDC delta 0
- SUCCESS 0xbafc6739e19423ea69fcee095f0b012e5fa254101c1d841f77686132887eb456 status 1,
  gas 344,433, block 57,502,610: paid 56.552589 USDC for the cbBTC residue, **owner wallet
  +1.481324 USDC** (= the eth_call simulation). Executor afterwards: 0 USDC, 0 cbBTC,
  0 native, allowance to the comet 0.
- NOTHING-LEFT (same call again) 0xdb3286a0004a27459ac9dddddfc474a33c49fbe6fa9831e0e5b6b6006ad81524
  status 0, owner USDC delta 0.

Paper mode simulates the exact call with `eth_call` and a code override (the fork runtime,
`executor-runtime.hex`) at the fork address 0xfe00ddfe..8e9a, from the owner baked into that
runtime (0xc0ffee..02). Live mode uses the signer's address and `EXECUTOR_ADDR`.

## What the bot waits for

- Feed `/logs/base`, address = the comet, topic0 = AbsorbCollateral
  `0x9850ab1af75177e4a9201c65a2cf7976d5d28e40ef63494b44366f86b2f9412e` (199 events / 7 d,
  ~28/day in bursts). The first version waited on a wrong hash and a numeric cursor; both fixed.
- On `gap`, `removed`, HTTP 429 / 503 / 400 or a connection error: re-read the reserves
  through the relay (at most once a minute while the feed is down), then continue.
- Safety poll of the reserves every 10 min.
- Routed collaterals: WETH (pool 0xd0b53d92..f224) and cbBTC (pool 0xfbb6eed8..43ef), both
  UniV3 0.05 %. Other collaterals are not tried.

## Send rule and loss bound

Send only when the simulated surplus (USD) is above that send's gas cap:
`500,000 gas x maxFeePerGas x 4,000 USD/ETH + 0.02 USD L1`, with `maxFeePerGas =
min(0.45 gwei, 2 x base fee + priority)` and priority = at most 25 % of gross. The cap is
below 0.92 USD by construction (`bot.py` loss-guard block and `attempt()`); `minProfit` in
the call is that cap, so a mined transaction either nets more than its gas cap or reverts
(`Cv3FlashBuy.sol` NoProfit check). Worst case per send = gas. Base native wallet 10 USD
(< 18 USD cap). Every send logs `send_result` with won / lost, gas used, gas cost, the
winner's block and how many blocks after it we landed.

## Reads

Safety poll: 2 collaterals x 1-2 `eth_call` x 144/day = up to 7.5k CU. Absorb wakes: ~28/day x
(4 reads + up to 2 sims + gasPrice) = ~5k CU. Feed: ~28 events x ~35 CU + ~4 CU/min
subscription = ~7k CU. Total ~20k CU/day = 0.011 USD/day at 0.53 USD per 1M CU; the bot
stops reading at 60k relay CU/day (`CU_CAP`).
