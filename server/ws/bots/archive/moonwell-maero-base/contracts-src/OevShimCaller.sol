// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

// Lead 72 mcbXRP leg proof caller. The mainnet whale winner (trace scratch/mw-xrp/trace-capture3.json)
// liquidated the mcbXRP-collateral position by calling mUSDC.liquidateBorrow(address,uint256,address)
// (selector 0xf5e3c462 on the shared delegate impl 0x85b3a4d84d5a6d5a8606968b223c3b4648d59d98) from a
// contract that answers the Chainlink-OEV caller-price guard: the price flow static-calls
// latestRoundData() (0xfeaf968c) and decimals() (0x313ce567) ON THE CALLER and the plain/EOA caller
// was returned code 3 for every repay size (attempts 774, scratch/mw-whale/proof21.json).
// This contract reproduces that context: it implements the feed interface by forwarding to the
// market's price aggregator and calls the entry once, requiring code 0.
interface IFeed {
    function latestRoundData()
        external
        view
        returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound);
    function decimals() external view returns (uint8);
}

contract OevShimCaller {
    IFeed public immutable feed;
    address public immutable usdc;

    constructor(address feed_, address usdc_) {
        feed = IFeed(feed_);
        usdc = usdc_;
    }

    function latestRoundData()
        external
        view
        returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound)
    {
        return feed.latestRoundData();
    }

    function decimals() external view returns (uint8) {
        return feed.decimals();
    }

    function approveUsdc(address spender, uint256 v) external {
        (bool ok, bytes memory d) = usdc.call(abi.encodeWithSelector(0x095ea7b3, spender, v));
        require(ok && (d.length == 0 || abi.decode(d, (bool))), "APPROVE");
    }

    // The one opportunity, one transaction: repay the borrower's USDC debt and take the
    // collateral shares. Reverts unless the entry reports code 0 (moonwell v2 success code).
    function liq(address mUsdc, address borrower, uint256 repay, address mColl) external returns (uint256) {
        (bool ok, bytes memory d) = mUsdc.call(abi.encodeWithSelector(0xf5e3c462, borrower, repay, mColl));
        require(ok, "ENTRY_REVERT");
        uint256 code = abi.decode(d, (uint256));
        require(code == 0, "LIQ_CODE");
        return code;
    }

    function redeem(address mColl, uint256 shares) external {
        (bool ok, bytes memory d) = mColl.call(abi.encodeWithSelector(0xdb006a75, shares));
        require(ok && (d.length == 0 || abi.decode(d, (uint256)) == 0), "REDEEM");
    }
}

// Negative control: same liquidateBorrow call, no feed shim on the caller.
contract NoShimCaller {
    function approveUsdc(address token, address spender, uint256 v) external {
        (bool ok, bytes memory d) = token.call(abi.encodeWithSelector(0x095ea7b3, spender, v));
        require(ok, "APPROVE");
    }

    function liq(address mUsdc, address borrower, uint256 repay, address mColl) external returns (uint256) {
        (bool ok, bytes memory d) = mUsdc.call(abi.encodeWithSelector(0xf5e3c462, borrower, repay, mColl));
        require(ok, "ENTRY_REVERT");
        uint256 code = abi.decode(d, (uint256));
        require(code == 0, "LIQ_CODE");
        return code;
    }
}
