trial (cheap-chain trial bot, decision 2026-11-17-cheap-chain-trials): feUSD discount -> Felix redemption round trip on HyperEVM.

# trial-feusd-redeem-hyperevm

## What it does

When feUSD trades below its redemption value in the HyperSwap V3 feUSD/USDT0 pool
(`0x44a59f78...`, 0.01%), one transaction through the executor `FeusdRedeemTake`:

1. flash-borrows USDT0 from Morpho Blue (`0x68e37dE8...`, no fee),
2. buys feUSD in the pool,
3. redeems it at Felix's CollateralRegistry (`0x9de1e570...`, permissionless `redeemCollateral`) for
   WHYPE + kHYPE,
4. sells kHYPE -> WHYPE, then sells exactly enough WHYPE -> USDT0 (exact output) to repay the loan,
5. unwraps the WHYPE that is left and pays it to the bot wallet as **native HYPE**.

The executor reverts `NoProfit()` unless the wallet receives at least `minProfitWei`, which the bot
sets to that send's whole gas cap (gas limit x maxFeePerGas). A lost attempt costs gas only.

Why native: the incumbent's profit ends in USDT0, which the farm neither counts nor sweeps. A
USDT0 -> USDC leg did not fit the 2,000,000 gas cap (attempts:1595). Leaving the profit in WHYPE and
unwrapping it removes one swap hop and the conversion: 1.75M gas on the fork at 640 USDT0.

## Last 7 days of competition (to 2026-11-17 05:40Z, attempts:1591/1595/1605, scratch/feusd-pnl.json)

| taker | route | calls | paid | gross/win (median, max) | gas/attempt | priority fee |
|---|---|---|---|---|---|---|
| EOA 0x0da1f154 via executor 0x1438e66b | Felix redemption (this route) | 96 | 83 | 0.066 / 0.87 USD | 0.018 USD (1.56-1.67M gas) | 0.03-0.05 gwei |
| EOA 0x6b78f490 via executor 0xe551a6cd | pool-only round trip, same spread | 27 | 3 | 0.067 / 0.117 USD | 0.023 USD | 0.0 gwei |

- 2 taker addresses, 86 paid round trips, incumbent net about +2.3 USD / 7 d. No fee auction so far.
- Blocks from takeable to taken were not derived per block. The bot's own path pinned to the block
  **before** four incumbent wins simulates a positive gain every time (selftest below), so each of
  those windows was open for at least one block (~1 s); the bot reacts in about 3 blocks.
- Expect mostly lost or never-sent attempts; the win rate is what the trial measures.

## Evidence

- Fork proof: `scratch/trial-feusd-redeem-hyperevm/proof.py` (result `proof-result.json`). The
  hyperevm fork serves head storage at any reset block, so the discount is created at head by a funded
  stranger selling feUSD into the pool (ordinary swaps, no code or storage override). The fix rerun
  at fork head 51490215 deployed in 1,160,496 gas, then succeeded in tx
  `0xb6e4c176b4f82356e947ff80a85e4b82e680020689a38bb8ed50723a70553998` with a net wallet
  gain of 0.664414141646606964 HYPE (1,738,449 gas). No-window tx
  `0x6ef9623ec57af6bdaf9acff5e027a3ad42dca761fd85a56834d8b65b45b614ba` reverted.
  USDT0, feUSD, WHYPE, kHYPE, native and all checked approvals were zero after success.
- Natural cases: `scratch/trial-feusd-redeem-hyperevm/selftest.py` runs this bot's `evaluate()` through
  the relay at historical blocks with the fork deployment's runtime as code override
  (`selftest-result.json`):

| block (before incumbent win) | pool price | size | simulated gain | incumbent's gross |
|---|---|---|---|---|
| 51292212 | 0.99503 | 640 USDT0 | 0.012836 HYPE (0.93 USD) | 0.869 USDT0 at 160 |
| 51284175 | 0.99600 | 640 | 0.012169 HYPE (0.90 USD) | 0.787 |
| 51359837 | 0.99805 | 320 | 0.002931 HYPE (0.23 USD) | 0.187 |
| 51431191 | 0.99081 | 80 | 0.001227 HYPE (0.094 USD) | 0.059 |
| head (08:13Z, price 1.00003) | - | - | all sizes revert (nothing to take) | - |

## Loss guard

- Executor: `NoProfit()` unless the owner's native balance grows by `minProfitWei` (contract lines 103, 106);
  `tx.gasprice <= maxGasPrice`, `deadline`, owner only.
- Bot: gas limit 1,950,000 (chain cap 2,000,000), `maxFeePerGas <= 2 gwei` hard, send only if
  gas limit x maxFeePerGas < 0.95 USD at (on-chain WHYPE/USDT0 price x 1.15) **and** simulated gain >
  that gas cap; `minProfitWei` = the gas cap. Priority bid at most 30% of simulated gross.
- A reverted attempt on the fork used 1,856,971 gas = 0.00019 HYPE (0.014 USD) at the 0.1 gwei base fee.

## Read cost

- Feed: one `/logs/hyperevm` filter, address `0x44a59f7859f199768e585133e0a5ab2da1350600`, topic0
  `Swap` `0xc42079f9...`. 3,217 Swap logs in 7 d = about 460/day x ~900 bytes x 0.04 = about 17k CU/day,
  plus ~5k CU/day subscription upkeep. A small pool, not a busy event.
- Relay: safety poll of `slot0` every 10 min (144 x 26 = 3.7k CU/day); simulations only while the pool
  price is at or under 0.999: up to 5 `eth_call` + 3 reads per evaluation, re-evaluated only after a
  further 0.05% drop or 10 min (worst case about 19k CU/day); hard cap 90,000 relay CU/day in code.
- Total about 30-45k CU/day = 0.016-0.024 USD/day at 1M CU = 0.53 USD.
- On feed `gap`, 429, 503 or a connection error the bot re-reads `slot0` through the relay.

## Logs (`logs/bot.jsonl`)

`start` (with `executor=`), `swap`, `poll`, `simulate_revert`, `opportunity_skip`, `opportunity`,
`paper_sim`, and live `send_result` with `result` won/lost, `gas_used`, `send_block`, `winner_block`
(nearest block where another address bought feUSD from the pool) and `blocks_after_winner`.

## Notes

- `take()` returns Felix's feUSD rounding remainder to the owner in the same transaction. The fork
  success left zero feUSD, USDT0, WHYPE, kHYPE, native balance and checked allowances in the executor.
  A different Felix collateral branch would need a separate route and proof before it is enabled.
- Live needs `EXECUTOR_ADDR` (or `EXECUTOR_ADDR_HYPEREVM`); the bot exits without it.
