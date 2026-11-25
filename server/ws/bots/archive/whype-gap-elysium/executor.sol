// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

// Holding-frame executor for lead 184: buy WHYPE with USDC in one Elysium UniV3-style
// pool when the pool trades at a discount to the HyperCore reference, sell it back in
// the SAME pool. Working capital (USDC) and the position (WHYPE) live in this contract;
// only exitAll() pays out to the bot wallet (gate stop / frame timeout).
// No baked execution targets: the pool is an argument of every entry; exitPool is set
// by the last successful buy because the frame ABI requires exitAll() with no args.

interface IERC20 {
    function transfer(address to, uint256 v) external returns (bool);
    function balanceOf(address a) external view returns (uint256);
    function approve(address sp, uint256 v) external returns (bool);
}

interface IUniV3Pool {
    // Elysium pool A slot0() measured at head returns exactly 6 words
    // (sqrtPriceX96, tick, observationIndex, observationCardinality,
    //  observationCardinalityNext, feeProtocol/unlocked-packed).
    function slot0() external view returns (uint160 sqrtPriceX96, int24 tick, uint160, uint160, uint160, uint160);
    function token0() external view returns (address);
    function token1() external view returns (address);
    function fee() external view returns (uint24);
    function swap(address recipient, bool zeroForOne, int256 amountSpecified, uint160 sqrtPriceLimitX96, bytes calldata data)
        external returns (int256 amount0, int256 amount1);
}

contract WhypeGap {
    address public immutable bot;
    IERC20 public constant USDC = IERC20(0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65);
    IERC20 public constant WHYPE = IERC20(0xbA876237B0F021A6c6D852d6c26E107997cC5E81);

    uint160 internal constant MIN_SPL = 4295128740; // MIN_SQRT_RATIO + 1
    uint160 internal constant MAX_SPL = 1461446703485210103287273052203988822378723970341;

    address public exitPool;   // set by each successful buy; exitAll() has no args (frame ABI)
    address internal swapPool; // pool mid-swap; the callback may only be called by it

    event Buy(address pool, uint256 usdcIn, uint256 whypeOut, uint256 exitQuote);
    event Sell(address pool, uint256 whypeIn, uint256 usdcOut);
    event ExitAll(uint256 whypeIn, uint256 usdcOut);

    modifier onlyBot() {
        require(msg.sender == bot, "NOT_BOT");
        _;
    }

    constructor() {
        bot = msg.sender;
    }

    /// USDC that selling whypeAmt would fetch at the pool's current spot, minus the
    /// pool's current fee(): the pool raw price sqrtP^2/2^192 is token1-per-token0,
    /// so raw USDC (token0, 6dp) received for raw WHYPE (token1, 18dp) is
    /// whypeAmt << 192 / sqrtP^2. (whypeAmt << 192) fits uint256 up to ~18.4 WHYPE
    /// (~1200 USD), far above holding_usd 100. Approximation (no tick-crossing) is intentional:
    /// positions are < 0.2% of pool A depth.
    function quoteExit(address pool, uint256 whypeAmt) public view returns (uint256) {
        (uint160 sqrtP, , , , , ) = IUniV3Pool(pool).slot0();
        uint256 raw = (whypeAmt << 192) / (uint256(sqrtP) * uint256(sqrtP));
        uint24 f = IUniV3Pool(pool).fee();
        return raw * (1_000_000 - uint256(f)) / 1_000_000;
    }

    /// Buy WHYPE with usdcIn of this contract's USDC in `pool`.
    /// Reverts unless (a) minWhypeOut received, and (b) the received WHYPE would sell
    /// back into the same pool right now for at least minExitUsdc (frame guard: no
    /// entry that is already under water beyond the bot's stated tiny loss).
    function buy(address pool, uint256 usdcIn, uint256 minWhypeOut, uint256 minExitUsdc) external onlyBot {
        require(usdcIn > 0 && USDC.balanceOf(address(this)) >= usdcIn, "NO_USDC");
        require(IUniV3Pool(pool).token0() == address(USDC) && IUniV3Pool(pool).token1() == address(WHYPE), "POOL_PAIR");
        uint256 w0 = WHYPE.balanceOf(address(this));
        swapPool = pool;
        USDC.approve(pool, usdcIn);
        IUniV3Pool(pool).swap(address(this), true, int256(usdcIn), MIN_SPL, "");
        USDC.approve(pool, 0);
        swapPool = address(0);
        uint256 got = WHYPE.balanceOf(address(this)) - w0;
        require(got >= minWhypeOut, "MIN_WHYPE");
        uint256 q = quoteExit(pool, got);
        require(q >= minExitUsdc, "GUARD_EXIT");
        exitPool = pool;
        emit Buy(pool, usdcIn, got, q);
    }

    /// Sell the WHYPE held in this contract back into `pool`, keeping the USDC here.
    /// Reverts unless at least minUsdcOut is received (worst case of a failed sell: gas).
    function sell(address pool, uint256 minUsdcOut) external onlyBot {
        uint256 w = WHYPE.balanceOf(address(this));
        require(w > 0, "NO_WHYPE");
        uint256 u0 = USDC.balanceOf(address(this));
        swapPool = pool;
        WHYPE.approve(pool, w);
        IUniV3Pool(pool).swap(address(this), false, int256(w), MAX_SPL, "");
        WHYPE.approve(pool, 0);
        swapPool = address(0);
        uint256 got = USDC.balanceOf(address(this)) - u0;
        require(got >= minUsdcOut, "MIN_USDC");
        emit Sell(pool, w, got);
    }

    /// Frame exit: owner-only, no arguments (gate ABI). Sells all WHYPE held via the
    /// pool of the last buy and sends ALL USDC (proceeds + idle capital) to the bot
    /// wallet, plus any native left here. Never reverts when nothing is held.
    function exitAll() external onlyBot {
        uint256 w = WHYPE.balanceOf(address(this));
        uint256 u0 = USDC.balanceOf(address(this));
        if (w > 0) {
            address p = exitPool;
            require(p != address(0), "NO_EXIT_POOL");
            swapPool = p;
            WHYPE.approve(p, w);
            IUniV3Pool(p).swap(address(this), false, int256(w), MAX_SPL, "");
            WHYPE.approve(p, 0);
            swapPool = address(0);
        }
        uint256 u = USDC.balanceOf(address(this));
        if (u > 0) require(USDC.transfer(bot, u), "USDC_OUT");
        if (address(this).balance > 0) {
            (bool ok, ) = bot.call{value: address(this).balance}("");
            require(ok, "NATIVE_OUT");
        }
        emit ExitAll(w, u - u0);
    }

    function uniswapV3SwapCallback(int256 a0, int256 a1, bytes calldata) external {
        address p = swapPool;
        require(msg.sender == p, "CALLBACK");
        if (a0 > 0) require(USDC.transfer(p, uint256(a0)), "PAY0");
        if (a1 > 0) require(WHYPE.transfer(p, uint256(a1)), "PAY1");
    }

    receive() external payable {}
}
