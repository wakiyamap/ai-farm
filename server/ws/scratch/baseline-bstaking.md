## Overview

BStaking handles bToken staking and pro-rata protocol fee rewards. A reward accumulator streams pool fees and pays them in the reserve asset, so each staker's claim grows with the pool, not a fixed rate. The main drivers are:

1. Share of total stake: staked amount over total staked
2. Time staked: rewards accrue over time with the position
3. Trading volume: more pool fees mean more rewards to distribute

The pattern is designed to stay fair for early and late stakers. See `getAccumulator`, `getEarned`, and `getCurrentRate` for the current reward state.

## Functions

### Staking functions

#### deposit

Stakes bTokens to earn rewards. The caller transfers `_amount` bTokens into the protocol, while `_user` receives the staking position.

```solidity
function deposit(BToken _bToken, address _user, uint256 _amount) external
```

| Parameter | Type      | Description                       |
| --------- | --------- | --------------------------------- |
| `_bToken` | `BToken`  | The bToken to stake               |
| `_user`   | `address` | User receiving the stake position |
| `_amount` | `uint256` | Amount of bTokens to stake        |

#### withdraw

Withdraw unlocked staked bTokens for `msg.sender`.

```solidity
function withdraw(BToken _bToken, uint256 _amount) external
```

| Parameter | Type      | Description        |
| --------- | --------- | ------------------ |
| `_bToken` | `BToken`  | The staked bToken  |
| `_amount` | `uint256` | Amount to withdraw |

#### withdrawMax

Withdraw all currently unlocked bTokens for `msg.sender`.

```solidity
function withdrawMax(BToken _bToken) external
```

| Parameter | Type     | Description       |
| --------- | -------- | ----------------- |
| `_bToken` | `BToken` | The staked bToken |

#### withdrawAndClaim

Withdraw `_amount` of unlocked staked bTokens and claim pending rewards in one call.

```solidity
function withdrawAndClaim(BToken _bToken, uint256 _amount) external
```

| Parameter | Type      | Description               |
| --------- | --------- | ------------------------- |
| `_bToken` | `BToken`  | The staked bToken         |
| `_amount` | `uint256` | bToken amount to withdraw |

### Rewards functions

#### claim

Claim accumulated reserve rewards for `_user`.

```solidity
function claim(BToken _bToken, address _user, bool _asNative) external returns (uint256 amount_)
```

| Parameter   | Type      | Description                                              |
| ----------- | --------- | -------------------------------------------------------- |
| `_bToken`   | `BToken`  | The staked bToken                                        |
| `_user`     | `address` | User claiming rewards                                    |
| `_asNative` | `bool`    | Send wrapped native reserve as native ETH when supported |

Returns:

* `amount_`: reserve tokens claimed

### View functions

#### getEarned

Get unclaimed rewards for a user in the reserve asset.

```solidity
function getEarned(BToken _bToken, address _user) external view returns (uint256)
```

| Parameter | Type      | Description       |
| --------- | --------- | ----------------- |
| `_bToken` | `BToken`  | The staked bToken |
| `_user`   | `address` | User to query     |

Returns: `uint256`, reserve-denominated rewards not yet claimed.

#### getAccumulator

Preview the current global reward accumulator and distribution state for a pool.

```solidity
function getAccumulator(BToken _bToken)
  external view returns (uint256 accumulator_, uint256 newYield_, uint256 tokensPerSecond_)
```

| Parameter | Type     | Description   |
| --------- | -------- | ------------- |
| `_bToken` | `BToken` | Pool to query |

Returns:

* `accumulator_`: current reward accumulator
* `newYield_`: pending yield that would be distributed on sync
* `tokensPerSecond_`: current streamed reward rate

#### getCurrentRate

Get the current annualized reward distribution rate for a staked bToken.

```solidity
function getCurrentRate(BToken _bToken) external view returns (uint256)
```

| Parameter | Type     | Description   |
| --------- | -------- | ------------- |
| `_bToken` | `BToken` | Pool to query |

Returns: `uint256`, annualized reserve reward rate per staked bToken, scaled by the bToken decimals.

***

## Events

```solidity
event Deposit(BToken bToken, address user, uint256 amount, State.StakedAccount post);
event Withdraw(BToken bToken, address user, uint256 amount, State.StakedAccount post);
event Claim(BToken bToken, address user, uint256 amount);
event Liquidate(BToken bToken, address user, uint256 amount, State.StakedAccount post);
```

***

## Errors

| Error                           | Description                         |
| ------------------------------- | ----------------------------------- |
| `BStaking_StakeIsLocked`        | Attempting to withdraw locked stake |
| `BStaking_BTokenNotInitialized` | BToken pool is not initialized      |

***

## Usage Example

```solidity
// Stake 1000 bTokens
bToken.approve(address(bstaking), 1000e18);
bstaking.deposit(bToken, msg.sender, 1000e18);

// Check earned rewards
uint256 earned = bstaking.getEarned(bToken, msg.sender);

// Claim rewards as native ETH when the reserve supports it
uint256 claimed = bstaking.claim(bToken, msg.sender, true);

// Withdraw and claim in one tx
bstaking.withdrawAndClaim(bToken, 500e18);
```

***

## ABI

<MercuryAbi name="bStaking" />

***

## Related

* [Staking Guide](/docs/holders/stake) : How to stake
* [BLens Contract](/docs/contracts/blens) : View staking state
