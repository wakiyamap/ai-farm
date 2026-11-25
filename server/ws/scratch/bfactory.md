## Overview

BFactory deploys new `BToken` instances and creates pools. Only the recorded bToken deployer may `createPool` for that bToken. Entry points:

1. **createBToken**: deploy a minimal ERC-20 bToken and mint the total supply to the caller
2. **createPool**: connect a bToken to a reserve, Uniswap v4 pool, BLV, fees, and optional initial credit (Merkle claim + collateral/debt) via `CreateParams`
3. **precomputeBTokenAddress**: predict the create2 address of a bToken before deployment (salted per deployer)

`createPool` is payable for native-reserve funding; the Relay routes the shared component stack as for other `Component` calls.

## Factory functions

### createBToken

Deploys a new bToken. The full `_totalSupply` is transferred to `msg.sender`. The deployer is recorded in protocol state; only that address may call `createPool` for that bToken.

```solidity
function createBToken(string memory _name, string memory _symbol, uint256 _totalSupply, bytes32 _salt) external returns (BToken bToken_)
```

| Parameter      | Type      | Description                                                       |
| -------------- | --------- | ----------------------------------------------------------------- |
| `_name`        | `string`  | bToken name                                                       |
| `_symbol`      | `string`  | bToken symbol                                                     |
| `_totalSupply` | `uint256` | Full supply to mint to `msg.sender` (subject to on-chain min/max) |
| `_salt`        | `bytes32` | Salt for create2; combined with `msg.sender` in the hash          |

**Returns:** `BToken`, the new bToken instance

### createPool

`CreateParams` bundles bToken reference, pool reserves, active and BLV prices, creator, fee split, optional hook deployment, fee percentages, and optional initial credit (Merkle root, collateral, debt). The pool cannot already be initialized, and the caller must be the recorded deployer for `params.bToken`.

```solidity
function createPool(CreateParams calldata params) public payable
```

| Parameter | Type           | Description                                                                                                    |
| --------- | -------------- | -------------------------------------------------------------------------------------------------------------- |
| `params`  | `CreateParams` | BToken, reserve, initial liquidity, curve prices, fee split, optional hook, and optional initial credit fields |

#### CreateParams

```solidity
struct CreateParams {
    BToken bToken;
    uint256 initialPoolBTokens;
    address reserve;
    uint256 initialPoolReserves;
    uint256 initialActivePrice;
    uint256 initialBLV;
    address creator;
    address feeRecipient;
    uint256 creatorFeePct;
    uint256 swapFeePct;
    bool createHook;
    bytes32 claimMerkleRoot;
    uint256 initialCollateral;
    uint256 initialDebt;
}
```

<Callout id="book-price" title="Book price">
  Book price is useful for calculating initial pricing. It is the reserve backing per circulating bToken at launch: `bookPrice = reserves / circ`, where `reserves = initialPoolReserves + initialDebt` and `circ = totalSupply - initialPoolBTokens`.
</Callout>

| Field                 | Type      | Description                                                                                                                                                                                                                                                                                 |
| --------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bToken`              | `BToken`  | The bToken returned by `createBToken`. `msg.sender` must be the recorded deployer for this token.                                                                                                                                                                                           |
| `initialPoolBTokens`  | `uint256` | bToken amount transferred from `msg.sender` into the pool as initial unsold supply. Must be less than the bToken total supply; otherwise initial circulating supply is zero and curve initialization cannot price the pool correctly.                                                       |
| `reserve`             | `address` | Approved reserve token address. If funding with native ETH, this must be the configured wrapped native token.                                                                                                                                                                               |
| `initialPoolReserves` | `uint256` | Reserve token amount transferred from `msg.sender` into the pool. For ERC-20 reserves, approve the Relay first. For native ETH funding, send this amount as `msg.value`; excess ETH is refunded.                                                                                            |
| `initialActivePrice`  | `uint256` | Initial target active price in WAD precision. It must be greater than the pool's initial [book price](#book-price).                                                                                                                                                                         |
| `initialBLV`          | `uint256` | Initial/minimum BLV floor price in WAD precision. For normal deployers, `createPool` must initialize a standard quadratic curve; pass `0` to let the protocol compute the starting BLV for that quadratic curve. The resulting BLV must be less than or equal to [book price](#book-price). |
| `creator`             | `address` | Non-zero creator address recorded on the pool.                                                                                                                                                                                                                                              |
| `feeRecipient`        | `address` | Non-zero address that receives the creator share of fees.                                                                                                                                                                                                                                   |
| `creatorFeePct`       | `uint256` | WAD percentage of post-protocol fees paid to `feeRecipient` before staking fees. Must be `<= 1e18`; the remainder goes to staking.                                                                                                                                                          |
| `swapFeePct`          | `uint256` | Minimum swap fee in WAD precision. Must be between `0.0015 ether` (0.15%) and `0.5 ether` (50%).                                                                                                                                                                                            |
| `createHook`          | `bool`    | If `true`, initializes the Uniswap v4 hook pool for the bToken/reserve pair.                                                                                                                                                                                                                |
| `claimMerkleRoot`     | `bytes32` | Merkle root for optional initial credit claims. Use `bytes32(0)` when not launching with initial credit. Must be approved to use.                                                                                                                                                           |
| `initialCollateral`   | `uint256` | Optional bToken collateral reserved for initial credit. Must be zero unless `claimMerkleRoot` and `initialDebt` are both non-zero. Must be approved to use.                                                                                                                                 |
| `initialDebt`         | `uint256` | Optional reserve debt backing initial credit. Must be zero unless `claimMerkleRoot` and `initialCollateral` are both non-zero. When set, it is counted in initial total reserves. Must be approved to use.                                                                                  |

`claimMerkleRoot`, `initialCollateral`, and `initialDebt` are all-or-nothing: either all are empty/zero, or the root is non-zero and both amounts are positive. Initial credit also requires the deployer profile to be active and approved for credit deployment, and the resulting position must be solvent.

`createPool` transfers `initialPoolBTokens + initialCollateral` bTokens from the caller and transfers `initialPoolReserves` reserve tokens from the caller. Approve those amounts before calling unless the reserve side is funded with native ETH.

### precomputeBTokenAddress

Create2 address for the bToken that `createBToken` would deploy with the same name, symbol, total supply, salt, and deployer. Use the same `_deployer` you will use as `msg.sender` on `createBToken`.

```solidity
function precomputeBTokenAddress(string memory _name, string memory _symbol, uint256 _totalSupply, bytes32 _salt, address _deployer) external view returns (address computedAddress_)
```

| Parameter      | Type      | Description                                                              |
| -------------- | --------- | ------------------------------------------------------------------------ |
| `_name`        | `string`  | Must match the planned `createBToken` call                               |
| `_symbol`      | `string`  | Must match the planned `createBToken` call                               |
| `_totalSupply` | `uint256` | Must match the planned `createBToken` call                               |
| `_salt`        | `bytes32` | Must match the planned `createBToken` call                               |
| `_deployer`    | `address` | Address that will call `createBToken` (use `msg.sender` when you deploy) |

**Returns:** `address` (`computedAddress_`): the address the bToken would have at that create2 address

## Events

* **BTokenCreated**: bToken address, name, symbol, decimals, total supply, creator.
* **PoolCreated**: bToken, reserve, creator, fee recipient, fee and price parameters, pool id and capital totals (including initial credit when used).

## Errors

| Error                                | Description                                                    |
| ------------------------------------ | -------------------------------------------------------------- |
| `NotDeployer`                        | Caller is not the recorded deployer for this bToken            |
| `NotApprovedReserve`                 | Reserve token is not allowlisted for use                       |
| `PoolAlreadyInitialized`             | `createPool` called when a pool already exists for this bToken |
| `TotalSupplyTooLow`                  | `createBToken` supply below the protocol minimum               |
| `TotalSupplyTooHigh`                 | `createBToken` supply above the protocol maximum               |
| `InvalidName`                        | bToken name fails validation                                   |
| `InvalidSymbol`                      | bToken symbol fails validation                                 |
| `InvalidFeeRecipient`                | Fee recipient address is invalid                               |
| `InvalidCreator`                     | Creator address or role is invalid                             |
| `InvalidCreatorFee`                  | Creator fee `pct` or related value is invalid                  |
| `UnauthorizedCreditPositionCreation` | Initial credit setup is not permitted for this call            |
| `InvalidInitialCollateralOrDebt`     | Initial credit collateral or debt is inconsistent              |
| `InsolventInitialCreditPosition`     | Initial credit position would be insolvent                     |
| `InvalidPoolSupply`                  | Pool bToken / reserve supply inputs are invalid                |
| `InvalidSalt`                        | Salt does not meet create2 / validation rules                  |
| `InvalidConvexityExp`                | Convexity exponent for the curve is out of range               |

***

## ABI

<MercuryAbi name="bFactory" />
