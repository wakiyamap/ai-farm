## Overview

The BSwap contract implements Baseline's power-law AMM curve for token trading. It handles exact-in and exact-out buys and sells, plus matching quote functions for off-chain previews.

## Functions

### Trading Functions

#### buyTokensExactIn

Buy bTokens with an exact amount of reserves.

```solidity
function buyTokensExactIn(
  BToken _bToken,
  uint256 _amountIn,
  uint256 _limitAmount
) external returns (uint256 amountOut_, uint256 feesReceived_)
```

| Parameter      | Type      | Description                                      |
| -------------- | --------- | ------------------------------------------------ |
| `_bToken`      | `BToken`  | The bToken to buy                                |
| `_amountIn`    | `uint256` | Exact reserve amount to spend                    |
| `_limitAmount` | `uint256` | Minimum bTokens to receive (slippage protection) |

**Returns:**

* `amountOut_`: bTokens received
* `feesReceived_`: Fees attributed to the trade

***

#### buyTokensExactOut

Buy an exact amount of bTokens.

```solidity
function buyTokensExactOut(
  BToken _bToken,
  uint256 _amountOut,
  uint256 _limitAmount
) external payable returns (uint256 amountIn_, uint256 feesReceived_)
```

| Parameter      | Type      | Description                                     |
| -------------- | --------- | ----------------------------------------------- |
| `_bToken`      | `BToken`  | The bToken to buy                               |
| `_amountOut`   | `uint256` | Exact bTokens to receive                        |
| `_limitAmount` | `uint256` | Maximum reserves to spend (slippage protection) |

**Returns:**

* `amountIn_`: Reserves spent
* `feesReceived_`: Fees attributed to the trade

***

#### sellTokensExactIn

Sell an exact amount of bTokens.

```solidity
function sellTokensExactIn(
  BToken _bToken,
  uint256 _amountIn,
  uint256 _limitAmount
) external returns (uint256 amountOut_, uint256 feesReceived_)
```

| Parameter      | Type      | Description                                       |
| -------------- | --------- | ------------------------------------------------- |
| `_bToken`      | `BToken`  | The bToken to sell                                |
| `_amountIn`    | `uint256` | Exact bTokens to sell                             |
| `_limitAmount` | `uint256` | Minimum reserves to receive (slippage protection) |

**Returns:**

* `amountOut_`: Reserves received
* `feesReceived_`: Fees attributed to the trade

***

#### sellTokensExactOut

Sell bTokens to receive an exact amount of reserves.

```solidity
function sellTokensExactOut(
  BToken _bToken,
  uint256 _amountOut,
  uint256 _limitAmount
) external returns (uint256 amountIn_, uint256 feesReceived_)
```

| Parameter      | Type      | Description                                   |
| -------------- | --------- | --------------------------------------------- |
| `_bToken`      | `BToken`  | The bToken to sell                            |
| `_amountOut`   | `uint256` | Exact reserves to receive                     |
| `_limitAmount` | `uint256` | Maximum bTokens to sell (slippage protection) |

**Returns:**

* `amountIn_`: bTokens sold
* `feesReceived_`: Fees attributed to the trade

***

### Quote Functions

Quote functions return expected trade results without executing.

#### quoteBuyExactIn

```solidity
function quoteBuyExactIn(BToken _bToken, uint256 _amountIn)
  external view returns (uint256 tokensOut_, uint256 feesReceived_, uint256 slippage_)
```

**Returns:**

* `tokensOut_`: bTokens for `_amountIn` reserve (preview)
* `feesReceived_`: Fee portion of the quote
* `slippage_`: Price impact as a WAD-scaled ratio

#### quoteBuyExactOut

```solidity
function quoteBuyExactOut(BToken _bToken, uint256 _amountOut)
  external view returns (uint256 amountIn_, uint256 feesReceived_, uint256 slippage_)
```

**Returns:**

* `amountIn_`: Reserves required for `_amountOut` bTokens (preview)
* `feesReceived_`: Fee portion of the quote
* `slippage_`: Price impact as a WAD-scaled ratio

#### quoteSellExactIn

```solidity
function quoteSellExactIn(BToken _bToken, uint256 _amountIn)
  external view returns (uint256 amountOut_, uint256 feesReceived_, uint256 slippage_)
```

**Returns:**

* `amountOut_`: Reserves for `_amountIn` bTokens sold (preview)
* `feesReceived_`: Fee portion of the quote
* `slippage_`: Price impact as a WAD-scaled ratio

#### quoteSellExactOut

```solidity
function quoteSellExactOut(BToken _bToken, uint256 _amountOut)
  external view returns (uint256 tokensIn_, uint256 feesReceived_, uint256 slippage_)
```

**Returns:**

* `tokensIn_`: bTokens to sell to receive `_amountOut` reserves (preview)
* `feesReceived_`: Fee portion of the quote
* `slippage_`: Price impact as a WAD-scaled ratio

***

### View Functions

#### getCurveParams

Get current curve parameters for a bToken.

```solidity
function getCurveParams(BToken _bToken) external view returns (CurveParams memory)
```

**Returns:** `CurveParams` (`CurveLib`, WAD):

* `BLV`, `circ`, `supply`, `swapFee`, `reserves`, `totalSupply`, `convexityExp`, `lastInvariant` (curve state for pricing and invariant math)

***

## Events

```solidity
event Swap(
  BToken bToken,
  address user,
  uint256 activePrice,
  uint256 blvPrice,
  int256 bTokenDelta,
  int256 reserveDelta,
  uint256 totalFee,
  uint256 liquidityFee
);
```

***

## Errors

| Error              | Description                                                                 |
| ------------------ | --------------------------------------------------------------------------- |
| `SlippageExceeded` | Result would break the min/max slippage bound on the trade (`_limitAmount`) |
| `SolverFailed`     | Numerical solver failed to converge for the trade                           |

***

## Efficient Swap Paths For Integrators

BSwap exposes 4 swap functions, but only 2 are gas-efficient on-chain:

| Function             | Direction         | Gas       | Reason                          |
| -------------------- | ----------------- | --------- | ------------------------------- |
| `buyTokensExactOut`  | reserve to bToken | Cheap     | Direct curve computation        |
| `sellTokensExactIn`  | bToken to reserve | Cheap     | Direct curve computation        |
| `buyTokensExactIn`   | reserve to bToken | Expensive | Binary-searches for `amountOut` |
| `sellTokensExactOut` | bToken to reserve | Expensive | Binary-searches for `amountIn`  |

The `ExactIn`/`ExactOut` naming refers to what's exact from the user's perspective, but the on-chain cost depends on whether the contract receives the natural input to the curve math (direct computation) or the other side (binary search).

**Pattern for integrators:**

* **Buys:** Quote off-chain via `quoteBuyExactIn` (view call, solver is free), then execute via `buyTokensExactOut` with the quoted `amountOut`.
* **Sells:** Call `sellTokensExactIn` directly. It is already the efficient path.
* Never call `buyTokensExactIn` or `sellTokensExactOut` on-chain unless you can't pre-compute the amounts.

The [`@baseline-markets/sdk`](/docs/contracts/sdk) exposes the same pattern for TypeScript apps:

```ts
const quote = await sdk.quoteBuyExactIn(bToken, reservesIn);

await sdk.buyTokensExactOut(bToken, quote.tokensOut, maxReservesIn, {
  confirmations: 1,
});

await sdk.sellTokensExactIn(bToken, amountIn, minReservesOut, {
  confirmations: 1,
});
```

***

## Usage Example

Recommended buy flow: quote off-chain, then execute on the cheap path.

```solidity
// 1. Quote off-chain: how many bTokens does 100 reserves buy?
(uint256 quotedOut, uint256 quotedFee, uint256 slippage) = bswap.quoteBuyExactIn(
  bToken,
  100e18    // 100 reserves in
);

// 2. Execute via buyTokensExactOut with the quoted amount.
//    Apply slippage tolerance to the reserve cap (e.g. +1%).
uint256 maxIn = 101e18;
(uint256 amountIn, uint256 fees) = bswap.buyTokensExactOut(
  bToken,
  quotedOut,
  maxIn
);

// Sells are already on the efficient path. Call directly.
(uint256 amountOut, uint256 sellFees) = bswap.sellTokensExactIn(
  bToken,
  10e18,    // 10 bTokens in
  9e18      // min 9 reserves out (slippage)
);
```

***

## ABI

<MercuryAbi name="bSwap" />

***

## Related

* [BMM Mechanics](/docs/how-it-works/bmm): Power-law curve explanation
* [BLens Contract](/docs/contracts/blens) : View functions
