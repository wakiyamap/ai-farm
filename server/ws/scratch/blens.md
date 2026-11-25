## Overview

BLens exposes the read-only state that UIs, bots, and indexers need from the Mercury relay. It covers prices, pool balances, fees, staking, credit accounts, hook metadata, and router quote state.

Most calls take a `BToken _bToken`. The live relay address is the call target; BLens itself is installed as a component behind that relay.

## Price functions

### activePrice

Current market price in WAD precision (`1e18` = 1.0).

```solidity
function activePrice(BToken _bToken) external view returns (uint256)
```

### blvPrice

Current Baseline Value floor price in WAD precision.

```solidity
function blvPrice(BToken _bToken) external view returns (uint256)
```

### getBookPrice

Book-style price, computed as total reserves over circulating supply.

```solidity
function getBookPrice(BToken _bToken) external view returns (uint256)
```

### swapFee

Current swap fee from the maker curve params.

```solidity
function swapFee(BToken _bToken) external view returns (uint256)
```

Derived metrics such as premium are off-chain calculations. For example: `activePrice(bToken) - blvPrice(bToken)`.

## Pool state

```solidity
function reserve(BToken _bToken) external view returns (ERC20)
function totalReserves(BToken _bToken) external view returns (uint256)
function settledReserves(BToken _bToken) external view returns (uint256)
function pendingSurplus(BToken _bToken) external view returns (uint256)
function totalBTokens(BToken _bToken) external view returns (uint256)
function totalSupply(BToken _bToken) external view returns (uint256)
function getCirculatingSupply(BToken _bToken) external view returns (uint256)
function creator(BToken _bToken) external view returns (address)
function isPoolPaused(BToken _bToken) external view returns (bool)
```

Use these calls to read pool inventory, circulating supply, reserve accounting, creator ownership, and pause state.

## Fee state

```solidity
function creatorClaimable(BToken _bToken) external view returns (uint256)
function protocolClaimable(BToken _bToken) external view returns (uint256)
function pendingYield(BToken _bToken) external view returns (uint256)
function poolFeeRecipient(BToken _bToken) external view returns (address)
function creatorFeePct(BToken _bToken) external view returns (uint256)
function liquidityFeePct(BToken _bToken) external view returns (uint256)
function protocolFeePct(BToken _bToken) external view returns (uint256)
function poolFeeShare(BToken _bToken) external view returns (uint256 creator_, uint256 staking_)
function totalFeeShare(BToken _bToken) external view returns (uint256 creator_, uint256 staking_, uint256 protocol_)
```

`poolFeeShare` returns the creator and staking split after protocol fees. `totalFeeShare` returns the absolute creator, staking, and protocol shares.

## Staking state

```solidity
function claimableYield(BToken _bToken) external view returns (uint256)
function accumulator(BToken _bToken) external view returns (uint256)
function tokensPerSecond(BToken _bToken) external view returns (uint256)
function lastUpdatedTimestamp(BToken _bToken) external view returns (uint256)
function totalStaked(BToken _bToken) external view returns (uint256)
function withdrawable(BToken _bToken, address _user) external view returns (uint256)
function stakedPosition(BToken _bToken, address _user)
  external view returns (uint256 amount, uint256 locked, uint256 earned, uint256 userAccumulator)
```

`stakedPosition` returns raw tuple fields for the user's staking account.

## Credit state

```solidity
function totalCollateral(BToken _bToken) external view returns (uint256)
function totalDebt(BToken _bToken) external view returns (uint256)
function creditAccount(BToken _bToken, address _user)
  external view returns (uint256 collateral, uint256 debt)
```

`creditAccount` is the canonical read for a user's BCredit position.

## Quote and maker state

```solidity
function getMaker(BToken _bToken) external view returns (State.Maker memory)
function getQuoteState(BToken _bToken) external view returns (QuoteState memory state_)
function quoteLeverage(BToken _bToken, uint256 _collateralIn, uint256 _leverageFactor)
  external view returns (uint256 targetCollateral_, uint256 maxSwapReservesIn_, uint256 expectedDebt_, uint256 slippage_)
```

`getQuoteState` exposes the state off-chain routers need to reproduce BSwap quotes locally. `quoteLeverage` previews the target collateral, max swap reserves, expected debt, and slippage for a leverage action.

## Protocol and hook state

```solidity
function protocolFeeRecipient() external view returns (address)
function defaultProtocolFeePct() external view returns (uint256)
function defaultLiquidityFeePct() external view returns (uint256)
function originationFee() external view returns (uint256)
function timeToDistribute() external view returns (uint256)
function timeToAdapt() external view returns (uint256)
function poolIdToBToken(PoolId _poolId) external view returns (BToken)
function isProtocolPaused() external view returns (bool)
function isLocked() external view returns (bool)
function isApprovedCreditDeployer(address _user) external view returns (bool)
function reserveHoldings(ERC20 _reserve) external view returns (uint256)
function hasHook(BToken _bToken) external view returns (bool)
function poolKey(BToken _bToken) external view returns (PoolKey memory)
function getComponents() external view returns (Component[] memory components_)
```

## Usage example

```solidity
// Get current prices
uint256 marketPrice = blens.activePrice(bToken);
uint256 blv = blens.blvPrice(bToken);
uint256 premium = marketPrice - blv;

// Check pool state
uint256 reserves = blens.totalReserves(bToken);
uint256 circulating = blens.getCirculatingSupply(bToken);

// Preview leverage
(uint256 targetCollateral, uint256 maxIn, uint256 expectedDebt, uint256 slippage) =
  blens.quoteLeverage(bToken, 1000e18, 1e18);

// Check user positions
(uint256 staked, uint256 locked, uint256 earned,) = blens.stakedPosition(bToken, user);
(uint256 collateral, uint256 debt) = blens.creditAccount(bToken, user);
```

***

## ABI

<MercuryAbi name="bLens" />

***

## Related

* [BSwap Contract](/docs/contracts/bswap) : Trading functions
* [BCredit Contract](/docs/contracts/bcredit) : Borrowing functions
* [BStaking Contract](/docs/contracts/bstaking) : Staking functions
