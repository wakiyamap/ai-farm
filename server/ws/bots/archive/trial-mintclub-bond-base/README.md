trial

# trial-mintclub-bond-base

Cheap-chain trial (decision `2026-11-17-cheap-chain-trials.md`). Arbitrage between the two prices of a Mint Club V2
bonding-curve token on Base: the Bond's step price and the token's Uniswap v4 pool. First route: hDRB. No principal:
Morpho flash loan of WETH, profit paid to the bot wallet in native ETH.

## Mechanism

- **The curve.** Bond `0xc5a076cad94176c2996B32d8466Be1cE757FAa27` (verified `MCV2_Bond`; address from the DefiLlama
  adapter `projects/mint-club-v2`). `mint(token, tokensToMint, maxReserveAmount, receiver)` and
  `burn(token, tokensToBurn, minRefund, receiver)` are open to anyone: they mint or burn the token against its reserve
  token at the step price of the current supply, plus / less a royalty. `burn` spends the caller's allowance to the Bond.
  hDRB `0x23879479070377fafe1dc101fbb5d263696b9d61`: reserve DRB `0x3ec2156d4c0a9cbdab4a016633b7bcf6a8d68ea2`,
  royalties 1 pct each way, steps of 160,000 hDRB, each 1.86 pct above the last (2.4705 DRB per hDRB at placement).
- **The pools.** hDRB trades on a hookless Uniswap v4 pool against native ETH (fee 1 pct, tick spacing 200, id
  `0x4233d40e…ed78`, PoolManager `0x498581ff718922c3f8e6a244956af099b2652b2b`; slot0 shows a further 0.1 pct protocol
  fee). DRB trades against WETH on the Uniswap V3 1 pct pool `0x5116773e18a9c7bb03ebb961b38678e45e238923`.
- **The take**, one transaction through the executor `BondArb`:
  burn: flash WETH -> ETH -> hDRB (v4), `Bond.burn`, DRB -> WETH, repay;
  mint: flash WETH -> DRB, `Bond.mint`, hDRB -> ETH (v4) -> WETH, repay.
  `NoProfit` revert unless WETH + ETH grew by `minProfit`; everything is unwrapped and sent to the bot wallet.
  Fees on the round trip: 1.1 + 1 + 1 pct, so the pool must sit about 3.1 pct away from the curve.

## Competition, last 7 days (blocks 57476167-60500167, to 2026-11-21 19:46:49Z)

`scratch/rc3f9/bondhist.py` (every Bond Mint / Burn: 767 events, 85 on hDRB), `scratch/trial-mintclub-bond-base/windows.py`
(-> `windows.json`), `scratch/rc3f9/wraw.py` (profit from native balance diffs).

| operator (executor) | takes | profit a take | size | gas price, tx index |
|---|---|---|---|---|
| 0xc0ffee.. rotating senders, payout 0xc0ffeefeed8b9d27… (burn 0x13ff2141…, mint 0x818e056f…) | 37 burns + 26 mints | 0.0000169, 0.0000410, 0.0000663, 0.0002196 ETH (4 read) | 0.004-0.018 ETH, Morpho flash | 0.0052-0.0132 gwei, index 3-157 |
| 0x3de7e4a0 (0xf7c70a04…) | 15 burns | stays in its contract, not sized | 0.004-0.017 ETH | 0.0065-0.0076 gwei, index 3-154 |
| 0xf3f7364c (0x4d98dbc5…) | 4 burns | not sized | small | 0.0058-0.0060 gwei, index 6-21 |

Blocks to take (from the newest other trade on the hDRB v4 pool to the take; 41 of the 82 takes have one within 3,000
blocks, the rest were opened by the DRB pool moving): median 651 blocks = 130 s, minimum 15 blocks = 3 s, 33 of 41 over
30 s, 27 over 60 s, none in the same block. Priority-fee level: none; everybody pays about the base fee and lands at
whatever index. Gas a take: 1.47-1.56M = 0.000009-0.000018 ETH (0.015-0.03 USD at about 1,670 USD/ETH, the price noted
in today's kDIEM README, not re-measured). Takes per day, oldest first: 23, 0, 29, 10, 0, 6, 14.

## The bot

- Timer, one Multicall3 `eth_call` every 30 s: the v4 pool's slot0 through `PoolManager.extsload` (slot
  `keccak(id, 6)` from `cast index`), the V3 pool's `slot0()` and `Bond.priceForNextMint(token)`. Routes are in
  `routes.json` (one today; another Mint Club token fits if it has a hookless v4 native-ETH pool and its reserve token
  has a WETH V3 pool).
- Screen in floats: marginal round trip after pool fees and royalty above 0.2 pct (at the parents of the two proof
  takes it read 0.68 and 1.10 pct).
- A candidate is simulated with the exact `run()` (`eth_call`) at 0.002, 0.005, 0.01, 0.02, 0.04, 0.08 ETH until the
  gain stops growing. Below 0.000005 ETH: logged once as `below_interest`. Otherwise base fee, `eth_estimateGas`, gas
  limit = estimate x 1.2, priority fee = at most 1/10 of gross spread over the gas limit and at most 0.1 gwei, max fee =
  base fee x 1.25 + tip (never above 0.15 gwei), `cap = gasLimit x maxFee + L1 allowance`. Sends only when
  gross > 1.3 x cap, with `minProfit = cap` (both in wei, no price needed). At today's base fee the cap is about
  0.000013 ETH, so the send line is about 0.000017 ETH: the smallest incumbent takes are below it and are skipped.
- Mint direction: `tokensToMint` is sized off-chain to use 99.5 pct of the DRB the WETH buys; the executor sells what
  is left back. A mint that would cross a step boundary reverts in the simulation and is not sent.
- Log lines (`logs/bot.jsonl`): `start`, `heartbeat`, `check`, `opportunity`, `opportunity_skip`, `simulate_revert`,
  `paper_sim`, `signer_reject`, `send_result` (won / lost, gas used, send block, winner block, tx index), `read_budget`.
- Live: `EXECUTOR_ADDR_BASE` or `EXECUTOR_ADDR` required; the signer's address (`my_address()["address"]`) is `from`.

## Read cost

1 `eth_call` (26 CU) every 30 s = 2,880 a day = 74,880 CU/day; a candidate adds up to 6 `eth_call`, a block read, an
estimate and a guard call (about 250 CU), a send a receipt poll and one `eth_getLogs`. Budget 78,000 CU/day =
0.041 USD/day at 1M CU = 0.53 USD; hard cap in code 95,000 CU/day (then sleeps to 00:00 UTC; every read, the first
included, is inside the loop's handler). No feed filter (the PoolManager's Swap event is a busy event).

## Proof

`scratch/trial-mintclub-bond-base/proof.py` (one lease, two resets): at the parents of an incumbent burn take (block
60479958) and mint take (block 60052080) the bot's own read, screen, size and calldata give a success paying the owner
+0.00001689 ETH and +0.0000359 ETH, with NotOwner, NoProfit guard, repeat and opposite-direction reverts. Details and
hashes in `manifest.yaml` `fork_evidence` and `proof-result.json`.
