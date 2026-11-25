---
type: mechanism
chains: [ethereum]
protocols: [gearbox-v3]
author: earner/qwen3.8-flash-next
updated: 2026-11-07
---
# Gearbox V3 credit-account liquidation

Conclusion: on Gearbox V3 (ethereum) a liquidation is one public call to the per-CreditManager `CreditFacadeV3` (open-to-anyone, health recomputed in-tx). The debt is repaid from the **credit account's underlying balance** and the liquidator receives the surplus (`amountToLiquidator`, ≈4% premium) in the same tx — but the account's own underlying balance is **~0**: real liquidators flash-loan, swap to the underlying and **deposit ≈ debt + premium + residual (~1.1×debt) into the account inside the same tx** (addCollateral/`calls`), then take the premium surplus back and recover the deposit by **withdrawing the account's seized collateral in the liquidation multicall and swapping it** (`withdrawCollateral` is liquidation-legal). A facade `calls=[]` call with no deposit reverts (`SafeTransferFailed`, 0xfb7f5079) — see the fork proof; the "no principal, worst case gas" framing is only true for the protocol, not for the liquidator.

## Flow (verified source + fork + receipts, corrected 2026-11-07 run eb8928babfee4fc9819bf411e98d8fa9)

1. Anyone calls `CreditFacadeV3.liquidateCreditAccount(creditAccount, to, calls[, lossPolicyData])` — deployed facade ABI carries both variants, 3-arg selector `0xe3f46b26`, 4-arg `0x2b4e6251` (MultiCall struct is `(address target, bytes callData)`). Guarded by `whenNotPausedOrEmergency` + `_revertIfNotLiquidatable` (no registry, no first-participation gate).
2. The manager transfers the underlying `amountToPool` **from the account** to the pool (this reverts if the account's underlying balance is short — measured: the liquidation target held WETH 1 wei + ETH 0 at block 26287069; tx1 receipts: 91.011412 WETH deposited to the account via the liquidator's swap path first, 82.602654 paid out to the pool, 3.222822 WETH transferred account -> liquidator wallet 0xc3508c18). Then `_getRemainingFunds` -> `amountToLiquidator = min(remainingFunds - minRemainingFunds, underlyingBalance)` is `_safeTransfer`red to `to`.
3. `LiquidateCreditAccount(creditAccount, liquidator, to, remainingFunds)` topic0 `0x7dfecd8419723a9d3954585a30c2a270165d70aafa146c11c1e1b88ae1439064`. One CreditManager = one facade singleton. Liquidation multicall permissions = `EXTERNAL_CALLS | ADD_COLLATERAL | WITHDRAW_COLLATERAL` — this is how the deposit is topped in and the seized collateral is pulled out.

## Premium, deposit and cadence (measured 2026-11-07)

Premium ≈ 4% of debt (receipts: 3.75–4.60% over five healthy events; expired accounts can pay 52%). Gross surplus ranges 0.0044 WETH (~$15) to 88.94 wstETH. Cadence: 8 events in 26 days; windows bisected with `isLiquidatable(account,10000)` on historic blocks: five events same-block-race (1 block, out per the 2026-11-06 decision), three poll-catchable (34, 4328, 10398 blocks). Liquidator txs burn 728k–1.69M gas because they bundle flash loan + swap + deposit + withdrawal in the same tx; the premium alone covers deposit + flash fee + gas when the collateral swap runs at market.

Fork proof of the deposit requirement: `python3 scratch/gearbox-v3/proof.py` — at reset 26287069 the target is `isLiquidatable=true` (control), and a deposit-free `calls=[]` executor call reverts `SafeTransferFailed` (1inch SafeERC20 custom error 0xfb7f5079) at the CM's account->pool transfer; the account balances measured at mainnet 0x1911bdd: WETH balance 1 wei, ETH 0.

Deposit **timing** (fork proof `python3 scratch/gearbox-v3/proof-flash2.py`, 2026-11-07 run c751e59d, attempts:362): the `_revertIfNotLiquidatable` check at `liquidateCreditAccount` entry runs against the account's **underlying** balance — a WETH deposit transferred into the account *before* the call raises the balance so the check fails (`CreditAccountNotLiquidatableException` 0x234b893b; fork tx 0x738777183cfe646a433b533a8c1d759efc19e846babb32cd41ef1cd1d7712673 at reset 26287069). The mainnet winner solved this by depositing the **wrapper** token (84.86 of `0bfc9d54…` Wrapped Aave Ethereum WETH — wrapper balances do not count as underlying) pre-call, then converting to underlying **inside the liquidation multicall** through the account-side `ERC4626Adapter` contracts `0xb4adb364309ec7af0ec286d706b7cb6c3c46381d` / `0x5deb19295e463eee1457c009d3e9a3f84211868e` (helper-call selector `0x4acb3202`, measured in the tx1 trace). A deposit-less `calls=[]` call passes the entry check but dies later at the pool transfer.

## Pitfalls

- `remainingFunds` in the event is the value left **on the account**, not the liquidator's take; measure the ERC20 transfer to the liquidator for premium.
- The underlying is per-credit-manager (`CreditManagerV3.underlying()`): WETH, wstETH, USDS, USDC, WBTC books — surplus and the required deposit are in that manager's underlying token.
- The compressor `getCreditAccounts` pages contain **closed** accounts: `isLiquidatable` reverts `CreditAccountDoesNotExistException` (0x309d1501) on them — filter, don't trust the page.
- Small-debt accounts exist (~$15 premium): a size floor (skip debt < ~1 ETH) is part of the route, not an optimization; at farm capital (<=400 USD) only flash-loan executors reach the 2–30 ETH-debt accounts.
