trial: ICHI vaults on Base (Hydrex / Trebleswap), flash deposit + withdraw versus another pool.

## What it does

ICHI vaults take single-sided deposits priced at their own pool (spot / TWAP) and pay withdrawals pro-rata in both
tokens. When the vault's other token is worth more on another pool, one transaction through the `IchiVaultArb3`
executor: Morpho Blue flash loan of the deposit token -> `vault.deposit` -> `vault.withdraw` -> one swap on a
PancakeSwap V3 or Slipstream-style pool (exact-in sale of the other token, or exact-out purchase of the shortfall)
-> repay -> gain to the bot wallet as native ETH (WETH unwrapped) or USDC. The executor reverts unless the gain is
at least `minProfit` (= this send's gas cap), so a lost attempt costs gas only.

Covered vaults (8) and closing pools: see `ROUTES` in `bot.py`. Not covered: FACY, EURC, cbLTC, cbETH, HYDX vaults.

## Competition, last 7 days (blocks 57,060,715-60,084,715, to 2026-11-20 20:45Z)

Source: `scratch/ichi-f22b/measure-base.json` (gain = net token transfers to tx.from + tx.to, a floor).

- One operator: 87 EOAs with the prefix `0xc0ffee`, 38 contracts, payout to `0xc0ffeefeed8b9d271445cf5d1d24d74d2ca4235e`.
- Covered vaults: 473 round trips (67 a day), 0.02608 WETH (41.6 USD); median take 0.0000127 WETH (0.02 USD).
- Takes of 0.00002 WETH or more: 161, sum 0.02365 WETH (37.8 USD); fee share of gross median 11.6 pct; gas price
  median 0.0083 gwei (base fee about 0.006 gwei); 106 of 161 at tx index 10 or later.
- Takes of 0.0002 WETH or more: 20, sum 0.01474 WETH (23.5 USD); gas price median 0.029 gwei; tx index 2 to 142.
- Blocks to take: not measured per gap. Both fork-proven gaps were open at the parent block of the incumbent's take.
- Priority-fee level: most takes pay the base fee only; the larger ones 0.01-0.2 gwei.

## Send rule

Send only if simulated gain >= 1.2 x (gas limit x maxFeePerGas + L1 fee bound); the cap stays under 0.95 USD;
priority-fee bid at most 35 pct of gross. Log line per send: `send_result` with `won` / `lost`, `gas_used`,
`winner_block`, `blocks_after_winner`.

## Read cost

One `eth_call` (scan, 37 candidates) every 27 s = 3,200 x 26 CU = 83,200 CU/day, price read every 15 min 2,500 CU,
about 140 CU per evaluated gap. Hard cap 98,000 CU/day in code (0.052 USD at 1M CU = 0.53 USD). No feed filter:
the gap opens on swaps of busy pools.

## Files

- `bot.py`, `run.sh`, `executor-runtime.hex` (paper code override = `eth_getCode` of the fork deployment)
- Executor source: `scratch/trial-ichi-vault-base/contracts/src/IchiVaultArb3.sol`
- Fork proof: `scratch/trial-ichi-vault-base/proof.py` (`proof.json`, `proof-exactin.json`), self-test `selftest.py`
- Live: `EXECUTOR_ADDR_BASE` or `EXECUTOR_ADDR` is required; the bot exits without it.
