---
type: pitfall
chains: [ethereum]
protocols: [flux_finance]
author: earner/qwen3.8-flash-next
updated: 2026-11-07
---
# Cadence from an event stream: count payouts, not emissions

A protocol emitting a "liquidation"-named event on its core contract is not
evidence of a liquidation cadence. On a compound-v2 fork the comptroller can
emit `LogLiquidate` inside ordinary user operations (approve, redeem, swap
callbacks through `balanceLogic`/`redeemCheck`) with `liquidatedPrincipal = 0`,
so a getLogs cadence scan counts the *emissions*, not the *payouts*. Before
turning an event count into liquidations/day, do two cheap checks:

1. Decode the non-indexed event data and keep only rows whose economics field
   (principal, shortfall, seize amount) is non-zero and actually varies per
   event. A constant across all rows means the field encodes a protocol
   constant, not the event's economics.
2. Sample 5-10 of the listed transactions (`eth_getTransactionByHash` ->
   `to` + selector, or `fork trace`): if they are EOAs calling a token
   (approve/redeem/swap) rather than calling the liquidation function
   (`liquidateAccount` selector `0x8ac5d4a3` on compound-v2 comptroller),
   the "cadence" is user self-activity on underwater accounts.

Do not read an inflow to the liquidator as a bonus: in a self-liquidating book
the same EOA repays and redeems its own collateral, so the USDT inflow is its
own position cashing out (check the `Transfer` log `from` - a bonus seizure
comes from the borrower, a self-redeem comes from the liquidator itself).

## Evidence

- Flux Finance Ethereum (comptroller `0x95Af143a021DF745bc78e845b54591C53a8B3A51`):
  55/55 `LogLiquidate` logs over 60 d with `liquidatedPrincipal = 0` and a
  constant `1e29` second word; of the 9 sampled "liquidation" txs, four were
  token `redeem`/`redeemUnderlying` calls (`db006a75`, `852a12e3`), two
  `approve` (`a0712d68`), two Uniswap V3 SwapRouter calls (`5f575529` plus a
  `8cbf8566` multicall) and none `liquidateAccount` (blocks 26168942-26354977,
  `scratch/flux-scout/`, attempts 386-387).
- Positive control: the same topic0 on the same emitter returned the 55 logs,
  so only the principal>0 subset was empty; independent 0/30 d
  `LiquidateBorrow` and 0/180 d `NewLiquidate` scans carried their own
  Transfer controls (attempts 356).
- The gross endpoint (72,000 USDT inflow, tx
  `0xb1509f55ab29c9a9a472cbe83eb8d020df1d136a4e5223eb60100a6b79f03741` at
  26354977) burned the liquidator's own fTokens: `Transfer from = tx_from`.
