// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

// Diagnostic probe (run 1c1d2385): what does the moonwell mUSDC propagate
// entry (selector 0xf5e3c462 = liquidateBorrow(address,uint256,address) via
// the proxy fallback) return when the bot's executor sizes the repay at
// half the STORED principal? The aero1 success-phase tx reverts
// LIQUIDATE_REJECTED at the executor's require; callTracer shows the delegate
// completing accrue + getAccountLiquidity and returning a non-zero code
// WITHOUT reaching repay/seize. This probe performs the same approve +
// delegate call from an owner-funded caller and EMITS the returned code plus
// the same-block getAccountLiquidity words, so a mined receipt carries the
// answer without the executor's revert rolling it away.
interface IERC20P {
    function approve(address, uint256) external returns (bool);
}

interface ICompP {
    function getAccountLiquidity(address) external view returns (uint256, uint256, uint256);
}

contract Probe {
    event ProbeRet(uint256 code, uint256 liquidity, uint256 shortfall, uint256 amt);

    function go(address mUsdc, address holder, uint256 amt, address coll, address usdc, address comp)
        external returns (uint256)
    {
        IERC20P(usdc).approve(mUsdc, amt);
        (uint256 l, uint256 s, ) = ICompP(comp).getAccountLiquidity(holder);
        (bool okp, bytes memory rep) = mUsdc.call(
            abi.encodeWithSelector(bytes4(0xf5e3c462), holder, amt, coll));
        uint256 code;
        if (!okp) code = 1; // delegate reverted (unexpected: the executor saw no revert)
        else if (rep.length < 32) code = 2; // void return
        else code = abi.decode(rep, (uint256));
        emit ProbeRet(code, l, s, amt);
        return code;
    }
}
