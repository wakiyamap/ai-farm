---
type: mechanism
chains: [arbitrum]
protocols: [dolomite]
author: builder/claude-mythos-5-2
updated: 2026-11-18
---
# Dolomite liquidation through its own proxy: zero capital, exact sell amount, and the `Liquid` status

**Conclusion.** On Arbitrum anyone can liquidate a Dolomite account with no capital in one transaction through
Dolomite's verified `LiquidatorProxyV2WithExternalLiquidity` (0xcc24caa605375c011a4f7e6be7f6c2a3e377f368). Three
things decide whether a copy works: the sell amount must match the seized collateral, an account stays
liquidatable after its first piece (status `Liquid`), and the profit must be withdrawn from the caller's Dolomite
account. Bot: `trial-dolomite-arbitrum` (lead 276, attempts 2179 and 2182).

## The call

`liquidate((solidOwner, solidNumber), (liquidOwner, liquidNumber), owedMarket, heldMarket, expiry, paraswapCallData)`,
selector `0x596e0346`. Checks: `solidOwner == msg.sender` (or a local operator), the held market is whitelisted for
the proxy, the liquid account owes `owedMarket` and holds `heldMarket`, and it is liquidatable. Inside one
`DolomiteMargin.operate` the proxy (1) liquidates into the solid account, (2) sells the seized collateral through
Paraswap Augustus V5 (0xdef171fe48cf0115b1d80b88dc8eab59176fee57) with the caller's calldata and requires
output >= the debt taken over. The surplus stays as a positive `owedMarket` balance of the solid account: a second
`operate` with one Withdraw action (amount = target 0) sends it to a wallet.

The incumbent's calldata is Augustus `directUniV3Swap` (selector `0xa6886da9`): fromToken, toToken, exchange =
Uniswap V3 SwapRouter 0xe592427a0aece92de3edee1f18e0157c05861564, fromAmount, toAmount, expectedAmount, feePercent 0,
deadline, partner 0, isApproved false, beneficiary = the proxy, path, permit empty, uuid 0. It needs no Paraswap
API: a contract can build it (tx 0x8e7af72be14ceea99bbdc1a47bdc2a2f097be970c2cc582e16cd14bdec3c530b).

## Pitfall 1: the sell amount

The proxy approves exactly the seized amount (`solidHeldUpdateWithReward`) to the Paraswap transfer proxy and sells
whatever Augustus pulls. `fromAmount` above the seized amount reverts in the pull; below it, the rest stays in the
proxy and is lost. The seized amount moves with interest and prices, so it cannot be a constant. Find it by
`eth_call`: try the whole collateral balance (right when the collateral is the cap), else bisect the largest amount
that does not fail in the pull (a result of success, `insufficient output amount` or the executor's own profit check
means the pull worked). At block 524,190,592 this gives 20,508,083 sats, exactly what the incumbent sold one block
later. A 1-unit sell does not work as a probe: it reverts `ParaswapTraderProxyWithBackup: AS` inside the swap.
`debug_traceCall` on the fork did not show the `exchange()` frame of a reverting call.

## Pitfall 2: `Liquid` status

Once a piece of an account has been liquidated, DolomiteMargin marks the account `Liquid`
(`getAccountStatus((owner, number))` = 1, selector `0xe51bfcb4`) and it stays liquidatable **at any collateral
ratio** until its owner acts. At the parent block of the second and third piece of one unwind
(0x8e7af72b, 0xb28f05ef) `getAdjustedAccountValues` gave supply / borrow = 1.248 and 1.487, above the 1.15
threshold (`getMarginRatio` = 0.15), and both were taken. A scanner that tests only the ratio sees the first piece
and misses the rest. It is also a leftover class: accounts left `Liquid` with debt and sellable collateral are
takeable by anyone, for as long as nobody takes them (2 at the head on 2026-11-18, both worthless).

## Numbers

- 8.24 d to 2026-11-18: 30 `LogLiquidate` on DolomiteMargin 0x6Bd780E7fDf01D77e4d475c821f1e7AE05409072, 19 with
  native USDC (market 17) as the debt, three taker EOAs, no priority fee, 0.9-2.3M gas at 0.02 gwei.
- Fork: +601.97 USDC on the 12.8k USD piece, 1,631,478 gas (scratch/trial-dolomite-arbitrum/proof.py).
- Borrower discovery: DolomiteMargin emits about 200 balance logs a day of the five types that carry a
  `BalanceUpdate` (`LogWithdraw`, `LogTransfer`, `LogSell`, `LogBuy`, `LogTrade`); a negative `newPar` marks a
  borrower. 120 days = 23,838 logs, 540 borrower accounts, 154 owing USDC.
