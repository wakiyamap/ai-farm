## Overview

BController is Mercury's pool configuration and fee-distribution component, containing creator-specific functions and protocol admin controls. Below are creator-specific public functions.

## Creator Functions

### claimPoolFees

Claims accrued creator and protocol fees for a pool. Anyone can call this function. The contract first sweeps pending pool accounting, then sends creator fees to the pool's `feeRecipient` and protocol fees to the protocol fee recipient.

```solidity
function claimPoolFees(BToken _bToken) external
```

| Parameter | Type     | Description                                            |
| --------- | -------- | ------------------------------------------------------ |
| `_bToken` | `BToken` | Pool whose creator and protocol fees should be claimed |

### claimPoolFeesMulti

Claims accrued fees for multiple pools in one transaction.

```solidity
function claimPoolFeesMulti(BToken[] calldata _bTokens) external
```

| Parameter  | Type       | Description               |
| ---------- | ---------- | ------------------------- |
| `_bTokens` | `BToken[]` | Pools to process in order |

### setFeeRecipient

Updates the address that receives the creator share of claimed fees for a pool. Callable by the pool creator, Relay, or an executor while the pool is not paused.

```solidity
function setFeeRecipient(BToken _bToken, address _feeRecipient) external
```

| Parameter       | Type      | Description               |
| --------------- | --------- | ------------------------- |
| `_bToken`       | `BToken`  | Pool to update            |
| `_feeRecipient` | `address` | New creator-fee recipient |

### transferCreator

Transfers the recorded creator role for a pool. Callable by the current pool creator, Relay, or an executor while the pool is not paused.

```solidity
function transferCreator(BToken _bToken, address _newCreator) external
```

| Parameter     | Type      | Description         |
| ------------- | --------- | ------------------- |
| `_bToken`     | `BToken`  | Pool to update      |
| `_newCreator` | `address` | New creator address |

### modifyCreatorFeePct

Updates the creator fee split for a pool. This is a protocol-admin operation and must be less than or equal to `1e18` (100% in WAD precision).

```solidity
function modifyCreatorFeePct(BToken _bToken, uint256 _creatorFeePct) external
```

| Parameter        | Type      | Description                                                            |
| ---------------- | --------- | ---------------------------------------------------------------------- |
| `_bToken`        | `BToken`  | Pool to update                                                         |
| `_creatorFeePct` | `uint256` | WAD percentage of post-protocol fees paid to the creator fee recipient |

### pausePool

Pauses a single pool. Callable by an executor, Relay, or by the pool creator when that creator has an active deployer profile with `pauser` enabled.

```solidity
function pausePool(BToken _bToken) external
```

### unpausePool

Unpauses a single pool with the same authorization rules as `pausePool`.

```solidity
function unpausePool(BToken _bToken) external
```

## Events

```solidity
event FeesClaimed(address bToken, address reserve, uint256 creatorAmount, uint256 protocolAmount);
event CreatorTransferred(address bToken, address newCreator);
event FeeRecipientSet(address bToken, address feeRecipient);
event CreatorFeePctSet(address bToken, uint256 creatorFeePct);
event LiquidityFeePctSet(address bToken, uint256 liquidityFeePct);
```

## ABI

<MercuryAbi name="bController" />

***

## Related

* [Contracts Overview](/docs/contracts): Mercury deployment addresses
