## Overview

BCredit handles 0% interest borrowing and leverage against bToken collateral. Collateral is valued at BLV, debt is denominated in the reserve asset, and new debt pays an origination fee. Credit account reads live on [BLens](/docs/contracts/blens) through `creditAccount`.

## Borrowing functions

### borrow

Borrow reserves against the caller's unlocked staked bToken collateral. The contract locks the collateral required to keep the account solvent at BLV.

```solidity
function borrow(BToken _bToken, uint256 _amount, address _recipient) external
```

| Parameter    | Type      | Description                             |
| ------------ | --------- | --------------------------------------- |
| `_bToken`    | `BToken`  | The bToken collateral market            |
| `_amount`    | `uint256` | Reserve amount to borrow                |
| `_recipient` | `address` | Address that receives borrowed reserves |

### borrowNative

Borrow reserves and unwrap the native reserve when supported.

```solidity
function borrowNative(BToken _bToken, uint256 _amount, address _recipient) external
```

### repay

Repay reserve debt for `_recipient`. The caller pays `_reservesIn`, and the protocol unlocks collateral based on the repayment.

```solidity
function repay(BToken _bToken, uint256 _reservesIn, address _recipient) external
```

| Parameter     | Type      | Description                            |
| ------------- | --------- | -------------------------------------- |
| `_bToken`     | `BToken`  | The bToken credit market               |
| `_reservesIn` | `uint256` | Reserve amount to repay                |
| `_recipient`  | `address` | Credit account receiving the repayment |

### repayWithNative

Repay with native ETH when the market reserve supports native wrapping.

```solidity
function repayWithNative(BToken _bToken, address _recipient) external payable
```

## Leverage functions

### leverage

Create or increase a leveraged position by buying additional bToken collateral with borrowed reserves.

```solidity
function leverage(
  BToken _bToken,
  uint256 _totalCollateral,
  uint256 _collateralIn,
  uint256 _maxSwapReservesIn
) external returns (uint256 debt_)
```

| Parameter            | Type      | Description                                 |
| -------------------- | --------- | ------------------------------------------- |
| `_bToken`            | `BToken`  | The bToken to leverage                      |
| `_totalCollateral`   | `uint256` | Target total collateral after leverage      |
| `_collateralIn`      | `uint256` | Existing collateral supplied by the user    |
| `_maxSwapReservesIn` | `uint256` | Maximum reserves the internal buy may spend |

Returns:

* `debt_`: New debt added to the caller's account

### deleverage

Reduce leverage by selling bToken collateral for reserves and applying the proceeds to debt.

```solidity
function deleverage(
  BToken _bToken,
  uint256 _collateralToSell,
  uint256 _minSwapReservesOut
) external returns (uint256 collateralRedeemed_, uint256 debtRepaid_, uint256 refund_)
```

| Parameter             | Type      | Description                       |
| --------------------- | --------- | --------------------------------- |
| `_bToken`             | `BToken`  | The leveraged bToken              |
| `_collateralToSell`   | `uint256` | Collateral to sell into the curve |
| `_minSwapReservesOut` | `uint256` | Minimum reserves from the sale    |

Returns:

* `collateralRedeemed_`: bToken collateral unlocked or returned
* `debtRepaid_`: Reserve debt repaid
* `refund_`: Reserve refund when sale proceeds exceed debt

## Preview functions

```solidity
function getMaxBorrow(BToken _bToken, address _user) external view returns (uint256 maxBorrow_)
function getBorrowForCollateral(BToken _bToken, uint256 _collateral) external view returns (uint256 borrowAmount_, uint256 fee_)
function previewBorrow(BToken _bToken, address _user, uint256 _borrowAmount) external view returns (uint256 collateral_, uint256 debt_, uint256 fee_)
function previewDepositAndBorrow(BToken _bToken, address _user, uint256 _depositAmount, uint256 _borrowAmount) external view returns (uint256 collateral_, uint256 debt_, uint256 fee_)
function previewRepay(BToken _bToken, address _recipient, uint256 _reservesIn) external view returns (uint256 collateralRedeemed_, uint256 debtRepaid_)
function previewRebalanceCollateral(BToken _bToken, uint256 _collateral, uint256 _debt) external view returns (uint256 unlocked_)
```

Use `BLens.creditAccount(BToken _bToken, address _user)` to read a user's current `collateral` and `debt`.

## Credit claims

`claimCredit` installs Merkle-proven credit positions, used for migration and launch flows with precomputed credit accounts.

```solidity
function claimCredit(
  BToken _bToken,
  address[] calldata _users,
  uint128[] calldata _collaterals,
  uint128[] calldata _debts,
  bytes32[][] calldata _proofs
) external
```

## Events

```solidity
event Borrow(BToken bToken, address user, uint256 borrowed, uint256 fee, State.CreditAccount post);
event Repay(BToken bToken, address user, uint256 collateralRedeemed, uint256 debtRepaid, State.CreditAccount post);
event CreditClaim(BToken bToken, address[] users, uint128[] collaterals, uint128[] debts);
event Leverage(BToken bToken, address user, uint256 collateralAdded, uint256 debtAdded, uint256 collateralIn, uint256 reservesIn, State.CreditAccount post);
event Deleverage(BToken bToken, address user, uint256 collateralRedeemed, uint256 debtRepaid, uint256 collateralSold, uint256 refund, State.CreditAccount post);
```

***

## Errors

| Error                                        | Description                                            |
| -------------------------------------------- | ------------------------------------------------------ |
| `BCredit_RepaidMoreThanDebt`                 | Repaying more than owed                                |
| `BCredit_CannotRepayContract`                | Repayment recipient cannot be the relay itself         |
| `BCredit_Leverage_ZeroCollateral`            | Leverage with no target collateral                     |
| `BCredit_Leverage_InvalidStakedAmount`       | Supplied collateral is not below target collateral     |
| `BCredit_Leverage_BorrowAmountTooLow`        | Borrowed amount cannot fund the leverage buy           |
| `BCredit_Deleverage_InvalidCollateralToSell` | Invalid deleverage amount                              |
| `BCredit_Deleverage_Undercollateralized`     | Operation would leave the position undercollateralized |
| `BCredit_InvalidClaim`                       | Invalid Merkle credit claim                            |

***

## Usage Example

```solidity
// Borrow reserves against currently unlocked stake
bcredit.borrow(bToken, 900e18, msg.sender);

// Preview and execute leverage
(uint256 targetCollateral, uint256 maxIn,,) = blens.quoteLeverage(
  bToken,
  1000e18,
  1e18
);
bcredit.leverage(bToken, targetCollateral, 1000e18, maxIn);

// Repay reserve debt
reserve.approve(address(bcredit), 900e18);
bcredit.repay(bToken, 900e18, msg.sender);
```

***

## ABI

<MercuryAbi name="bCredit" />

***

## Related

* [Borrowing Guide](/docs/holders/borrow) : How to borrow
* [Multiply](/docs/holders/multiply) : How to use leverage
* [BLens Contract](/docs/contracts/blens) : Credit account reads and leverage quote
* [BLV Mechanics](/docs/how-it-works/blv): Why loans are 0% interest
