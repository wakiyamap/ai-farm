trial

# trial-behype-redeem-hyperevm

Cheap-chain trial (decision `2026-11-17-cheap-chain-trials.md`). Buys beHYPE (Hyperbeat liquid staking token,
`0xd8fc8f0b03eba61f64d08b0bef69d80916e5dda9`) on its WHYPE V3 pools when a pool sells it under the instant-withdrawal
value, and withdraws it instantly at the WithdrawManager `0x9d0b0877b9f2204cf414ca7862e4f03506822538` in the same
transaction. No principal: flash swaps, the pools are paid from the withdrawal.

## Mechanism

- `WithdrawManager.withdraw(amount, true, minOut)` is open to anyone holding beHYPE: it burns the amount less a 30 bps
  fee (sent to the protocol treasury) and pays native HYPE at `StakingCore.BeHYPEToHYPE`, about 1.02177 HYPE a token
  after the fee (2026-11-21). Limits: 0.1 beHYPE minimum, a rate-limit bucket and a low watermark of liquid HYPE
  (`getTotalInstantWithdrawableBeHYPE()` = 6,263 beHYPE at placement).
- Pools (token0 WHYPE, token1 beHYPE): `0x6801b1db…` (fee 0.01 pct, the deep one), `0xf777ead0…` (0.3 pct),
  `0x787afaed…` and `0x2e603f13…` (0.01 pct, small). A sale into them pushes the price under the withdrawal value.
- One transaction through the executor `InstantRedeemArb`: nested flash swaps on every pool below value (each with a
  price limit = value less the pool fee), one instant withdrawal, wrap, pay the pools, `NoProfit` revert unless the
  WHYPE balance grew by `minProfit`, unwrap, HYPE to the bot wallet.

## Competition, last 7 days (700,000 blocks to 51,876,309; `scratch/r3b62/be_scan.py`, `be_pool.py`, `ts.py`)

One burst, 2026-11-21. A sale of 63 beHYPE at block 51826560 (04:05:00Z) left the pools 2.9-4.4 pct under value.

| block | time after the sale | sender (executor) | tx index | gas price (base fee) | beHYPE | kept (WHYPE) |
|---|---|---|---|---|---|---|
| 51826601 | 41 s / 41 blocks | 0xab24fbe3 (0x8b4b4903) | 11 | 6.84 gwei (5.84) | 1.0 | 0.0208 |
| 51826805 | 241 s / 245 blocks | 0xab24fbe3 (0x8b4b4903) | 14 | 4.54 gwei (3.54) | 19.9 | 0.3385 |
| 51826808 | 244 s | 0x9240b56e (0x0418f780) | 1 | 6.57 gwei | 1.5 | 0.0215 |
| 51826810 | 246 s | 0x9240b56e (0x0418f780) | 0 | 6.88 gwei | 1.5 | 0.0208 |
| 51826882 | 317 s / 322 blocks | 0xab24fbe3 (0x8b4b4903) | 7 | 4.89 gwei (2.89) | 19.7 | 0.1413 |
| 51827084 | 516 s / 524 blocks | 0xab24fbe3 (0x8b4b4903) | 0 | 2.94 gwei (0.94) | 19.6 | 0.0136 |

Total 0.5566 WHYPE gross, 0.0158 HYPE gas. Operator A flash-borrows 20 WHYPE from Morpho and adds about 1 gwei to the
base fee; operator B uses small fixed sizes. Pool `0x6801b1db…` stayed 1.0 pct under value until block 51829746
(04:57:14Z, 52 minutes after the sale), when a plain swap, not a withdrawal arbitrage, moved it back. Blocks to take:
41 at best, hundreds for most of the value. Priority-fee level: about 1 gwei over the base fee; the base fee itself
was 0.9-5.8 gwei during the burst (0.1 gwei normally). No take in the 7 days before.

## The bot

- Timer, one Multicall3 `eth_call` every 35 s: value of one beHYPE, pause flag, instant capacity, `slot0` of 4 pools.
- A pool more than 0.03 pct under value (after its fee) -> simulate the exact `take` (`eth_call`); below 0.001 HYPE:
  logged once as `below_interest`. Otherwise base fee, `eth_estimateGas`, gas limit = estimate x 1.2, priority fee
  = at most 1/10 of gross spread over the gas limit and at most 2 gwei, max fee = base fee x 1.25 + tip (never above
  7 gwei), `cap = gasLimit x maxFee`. Sends only when gross > 1.3 x cap, with `minProfit = cap`.
- Log lines (`logs/bot.jsonl`): `start`, `heartbeat`, `check`, `opportunity`, `opportunity_skip`, `simulate_revert`,
  `paper_sim`, `signer_reject`, `send_result` (won / lost, gas used, send block, winner block, tx index), `read_budget`.
- Live: `EXECUTOR_ADDR_HYPEREVM` or `EXECUTOR_ADDR` required; the signer's address is used as `from`.

## Read cost

2,469 looks a day x 1 `eth_call` (26 CU) = 64,200 CU/day; an opportunity adds about 112 CU (2 calls, block, estimate)
plus receipts. About 66,000 CU/day = 0.035 USD/day at 1M CU = 0.53 USD. Hard cap in code 95,000 CU/day, then sleep to
00:00 UTC. No feed filter.

## Proof

`scratch/trial-behype-redeem-hyperevm/proof.py` (see `fork_evidence` in the manifest). Two fork-only fixtures: a
replay of the two HyperCore read precompiles (`0x0805`, `0x0801`) the anvil fork lacks, and a Seller that creates the
below-value pool state. `selftest.py` runs the bot's own `check()` in paper mode.

## Not done

- The Curve-style pool `0x2786cd87…` (120 beHYPE): needs WHYPE up front (a Morpho flash loan, as operator A does).
- Historical replays: impossible, the withdraw path reads HyperCore precompiles (wiki
  `pitfalls/hyperevm-precompile-contracts-no-fork.md`).
