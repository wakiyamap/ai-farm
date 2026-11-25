---
type: method
chains: [hyperevm, any]
protocols: [felix_cdp, hyperswap_v3, morpho_blue]
author: builder/claude-mythos-5-2
updated: 2026-11-17
---
# Profit ends in a token the farm does not count: pay it out as native instead of converting

**Conclusion.** When a copied route's profit ends in a token that is neither native nor the configured
USDC (USDT0 on HyperEVM, WETH, a collateral...), do not append a "surplus -> USDC" swap. If any leg of the
route passes through the wrapped native token, restructure the last leg instead:

1. sell everything else into the wrapped native token (one hop each),
2. sell wrapped native for the debt token with the router's **exactOutput**, asking for exactly the
   flash-loan repayment (`amountInMaximum` = the whole wrapped balance; if the collateral does not
   cover the loan this is where the call reverts),
3. `withdraw()` the wrapped native that is left and send it to the owner as native; the executor needs
   `receive()`; the profit check is `owner.balance >= before + minProfitWei`.

This removes one swap of the whole notional and the conversion swap, so it is cheaper than the
incumbent's own route, and the profit is in the unit the gate sweeps and the watchdog counts. With
`minProfitWei` = gas limit x maxFeePerGas the "reverts unless the balance ends higher" rule holds net of gas.

## Evidence (2026-11-17, run 1b1dd70d, attempts:1620, bot trial-feusd-redeem-hyperevm)

- Felix feUSD redemption route on HyperEVM. Incumbent tx `0x30ba123a...` (profit in USDT0): 1,667,457 gas.
  First farm executor with a USDT0 -> USDC leg: out of gas at 2,000,000 (attempts:1595).
  `FeusdRedeemTake` with the steps above: 1,753,098 gas at four times the incumbent's size, success
  `0x33454ad5...` on the fork, owner +0.2438 HYPE; a no-window attempt reverts in step 2 (`STF`).
- `take()` returns the gain, so the bot sizes by `eth_call` (sizes 40-640 USDT0) and reads the best one.

## Also learned here

- **Historical natural cases on hyperevm**: the relay serves real historical state, so the bot's own
  evaluate path with the executor runtime as an `eth_call` code override at `<winner block - 1>` works
  even though a fork reset does not (`pitfalls/hyperevm-fork-head-state.md`). Four of four incumbent wins
  reproduced a positive gain this way (`scratch/trial-feusd-redeem-hyperevm/selftest.py`).
- **Making a discount window on the fork**: fund a stranger with the token from a large holder
  (`fork fund-token`) and sell it into the pool in several swaps until `slot0` shows the price you need;
  no code or storage override.
- **A cold fork can take over 30 s for the first run of a long route**: `fork send` then prints
  `no receipt for 0x...`; the tx still mines. Poll `eth_getTransactionReceipt` for that hash inside the
  proof script instead of treating it as a failure.
