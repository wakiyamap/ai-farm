// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

// Atomic moonwell core-market (Compound v2 mToken) whale-liquidation executor
// for moonwell-whale-base (farm). One transaction: read the holder's shortfall
// from the moonwell comptroller, flash-loan USDC from Morpho Blue (0 fee),
// mUsdc.liquidateBorrow(holder, repay, mCollateral), redeem the newly seized
// collateral delta to its underlying, sell that delta back to USDC through ONE
// or TWO direct V3 pool swaps (swapData built by the bot with the pattern
// proven by the morpho-watcher-base executor: PancakeV3 / UniswapV3
// pool.swap(address recipient, bool zeroForOne, int256 amountSpecified,
// uint160 sqrtPriceLimitX96, bytes data) selector 0x128acb08, data =
// abi.encode(token0, token1); amountSpecified > 0 is the EXACT INPUT side
// (PancakeV3 semantics — opposite of UniV3); the pool pays the output token to
// the recipient and calls the V3 swap callback, which pays the pool the input
// token, bounded by the amount measured in THIS operation), repay the flash
// loan, then REVERT unless the executor's USDC balance ends higher than it
// started (>= minProfit + 1). Retained inventory cancels out in the
// before/after comparison, so it cannot mask a loss. Worst-case loss per
// transaction = gas only.
//
// Swap-route history: the UniV3 "SwapRouter02" address of record on Base
// (0x2626664c2603336e57b271c5c0b26f421741e481) carries NO exactInput entry in
// its deployed bytecode (measured 2026-11-05: fork eth_getCode has no
// 0x414bfbae dispatch; attempts 211/this run), so every router leg reverted.
// The measured whale winner tx
// 0x61e686eea746bb3b4b2bfaabec9a54fab1886b8d6a8aab3cb40b366d34cecdf9 instead
// calls the PancakeV3 pools directly (0x128acb08) — the pattern the
// fork-proven morpho-watcher-base executor uses; this contract copies that
// pattern. Pools are constructor-whitelisted (immutables P0/P1 +
// owner-extendable mapping), same as that executor.
//
// Copied from the winning whale flow measured on base (trace of tx
// 0x61e686eea746bb3b4b2bfaabec9a54fab1886b8d6a8aab3cb40b366d34cecdf9:
// flash -> liquidateBorrow(account, repay, collateral market) -> redeem ->
// pool swap(s), holder probed via comptroller.getAccountLiquidity(holder)).

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function approve(address, uint256) external returns (bool);
    function transfer(address, uint256) external returns (bool);
}

interface IMorpho {
    function flashLoan(address token, uint256 amount, bytes calldata data) external;
}

interface IComptroller {
    // getAccountLiquidity(address) returns (liquidity, shortfall, borrowLimit), 1e18-USD
    // (Compound v2 comptroller layout; measured 2026-11-10 run 12c9ed9f on the base fork at
    // the mcbXRP capture-1 resets 54911220/54922326/55160601: chronic-default holder
    // 0x544784a5 words [0, 31259/109738/17758 USD, 0] - liquidity zero (liquidatable),
    // the real shortfall in the SECOND word, borrowLimit zero for this chronically
    // underwater account. The previous source read the THIRD word (borrowLimit) as the
    // shortfall - it is 0 for this holder at every window, so the executor never fired.)
    function getAccountLiquidity(address account) external view returns (uint256, uint256, uint256);
}

interface IMToken {
    function liquidateBorrow(address borrower, uint256 borrowAmount, address mTokenCollateral) external;
    function redeem(uint256 redeemTokens) external;
    function underlying() external view returns (address);
    // underlying-token-unit borrow principal incl. accrued interest
    // (measured 2026-11-10 fork probes: actually UNDERLYING TOKEN units -
    //  mUSDC 647613944 (6-dec USDC) at holder 0xc8f8c2dd reset 55297681,
    //  mWETH 0.0379867e18 at the proof11 event).
    // NOT used for sizing: it accrues interest IN THE CALLING BLOCK (an
    // accrue phase of its own). The winning executor does not call it - it
    // accrues explicitly via accrueInterest() inside the liquidate tx and
    // then reads the same principal with borrowBalanceStored, which is exact
    // AT EXECUTION after that same-tx accrue (measured 2026-11-10 run this
    // session on the winner tx 0xf0579b9d trace: accrueInterest CALLs, then
    // borrowBalanceStored 0x95dd9193 STATICCALL, then the 0xf5e3c462 entry).
    function borrowBalanceCurrent(address account) external returns (uint256);
    // principal up to the LAST accrued block - a pure view, accrues nothing:
    // exact AT EXECUTION once this contract accrued the market with
    // accrueInterest() earlier in the same transaction (measured 2026-11-10
    // on the fork: mUSDC borrowBalanceStored(holder) = 647613941 vs
    // borrowBalanceCurrent 647613944 before any accrue).
    function borrowBalanceStored(address account) external view returns (uint256);
    // interest accrual entry: the winner recipe accrues the borrow AND
    // collateral markets INSIDE the liquidate tx, right before the propagate
    // entry, so borrowBalanceStored == the principal AT EXECUTION and repay
    // = principal/2 lands inside the tight repay band the entry enforces
    // (measured 2026-11-10 run this session: aero2.py bracket - at the
    // mAERO capture-1 reset every repay {half_stored+323, half_stored,
    // half_stored-323, half_stored-1USD, shortfall/2} returns code 3 when
    // the accrue tx is one block earlier (the stored principal lags one
    // block of interest); the winner tx 0xf0579b9d accrued INSIDE its own
    // tx (trace frames: accrueInterest calls, borrowBalanceStored
    // 0x95dd9193, then 0xf5e3c462 with amount 323806972 = exactly half of
    // 647613944) and passed).
    function accrueInterest() external;
}

contract MoonwellWhale {
    address public immutable COMPTROLLER; // moonwell comptroller (shortfall probe)
    address public immutable MORPHO;      // Morpho Blue (0-fee flashLoan)
    address public immutable USDC;        // the flash/loan/debt asset
    address public immutable OWNER;       // the bot's gate wallet (deployer)
    address public immutable P0;          // whitelisted swap pools (constructor)
    address public immutable P1;
    address public immutable P2;          // collateral-pool extension (cbBTC sell route, 2026-11-07 run 5fe750d4)
    address public immutable P3;          // collateral-pool extension (mEURC sell route leg1: PancakeV3 EURC/WETH fee100, lead 72 extension 2026-11-09)
    address public immutable P4;          // collateral-pool extension (mcbXRP sell route leg1: XRP/WETH pool 0xb90fe999..., lead 72 extension 2026-11-09 run this session: pinned from the incumbent trace tx 0xa59906ec - swap 0x128acb08, zeroForOne=false, positive exact input, callback 0xfa461e33, this contract's interface)
    address public immutable P5;          // mAERO sell route leg1: PancakeV3 AERO/cbBTC pool 0xdfe5f275020def30993f042174fc2d335678b626 (token0=AERO token1=cbBTC measured 2026-11-10; constructor-whitelisted 2026-11-10 fix round run 65d02323 per review a50ef674 item 1: a FRESH gate deployment needs no owner setPoolAllowed send before the first mAERO swap)
    address public immutable P6;          // mcbETH sell route leg1: UniV3 cbETH/WETH pool 0x257fcbae4ac6b26a02e4fc5e1a11e4174b5ce395 (token0=cbETH 0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22 measured at latest 2026-11-11; constructor-whitelisted 2026-11-11 fix round run 555959dc per review eb077fe8: pinned from the incumbent mcbETH liquidation trace tx 0x04dfa747208381ad7c2e3631dadae3e42a7cf9173cd3c6c53c1291facbf7d980 block 55828068 - mcbETH redeem -> swap cbETH->WETH on 0x257fcbae (0x128acb08, callback 0xfa461e33) -> the incumbent's second hop; our route reuses the proven P1 leg2)

    bool public inFlight;
    uint256 private collBefore; // executor's mToken balance before the active op

    // Armed-swap state: the pool currently owed the input side of the swap.
    // The V3 swap callbacks only pay while an authorized operation is active,
    // only from the armed pool, only for the armed pay token, bounded by the
    // amount measured in this operation.
    bool private armedSwap;
    address private activeSwapPool;
    address private activePayToken;
    uint256 private activePayMax;

    mapping(address => bool) public allowedPool;

    event Liquidated(address indexed account, address collateralMkt, uint256 repay, uint256 profitUsdc);
    event Swept(address indexed token, address indexed to, uint256 amount);
    event PoolAllowed(address indexed pool, bool allowed);

    constructor(address comptroller, address morpho, address usdc, address p0, address p1, address p2, address p3, address p4, address p5, address p6) {
        COMPTROLLER = comptroller;
        MORPHO = morpho;
        USDC = usdc;
        OWNER = msg.sender;
        P0 = p0;
        P1 = p1;
        P2 = p2;
        P3 = p3;
        P4 = p4;
        P5 = p5;
        P6 = p6;
    }

    function isPoolAllowed(address pool) public view returns (bool) {
        return pool == P0 || pool == P1 || pool == P2 || pool == P3 || pool == P4 || pool == P5 || pool == P6 || allowedPool[pool];
    }

    /// Owner may extend the pool whitelist (a newly measured pool for a newly
    /// discovered collateral). Owner-only; nothing else can widen the touchable inventory.
    function setPoolAllowed(address pool, bool allowed) external {
        require(msg.sender == OWNER, "ONLY_OWNER");
        allowedPool[pool] = allowed;
        emit PoolAllowed(pool, allowed);
    }

    /// Owner-only whale liquidation. `account` is the mToken borrower parameter
    /// (the LiquidateBorrow event's borrower field, e.g. the smart wallet),
    /// `holder` is the probed holder of the borrow (event holder field).
    /// Repay is sized from the live shortfall (half the shortfall, capped by
    /// maxRepay and, for a USDC borrow, by half the borrow balance; the mToken
    /// further caps inside liquidateBorrow; Morpho charges no premium, so a
    /// capped-down repayment is free). `borrowSwapData` is the pool calldata
    /// for USDC -> borrow underlying (ignored when the borrow underlying IS
    /// USDC); `sellSwapData1` sells the redeemed underlying (or its
    /// intermediate token) on the first pool; `sellSwapData2` + `sellPool2`
    /// (empty/zero = single hop) sell the intermediate token1 output of swap1
    /// on the second pool — the two-hop sale the measured whale winner used
    /// (WADO -> WETH -> USDC). Each swap's amount slot (the int256
    /// amountSpecified word, bytes [68:100) of the swap calldata) is
    /// overwritten with the exact amount THIS contract measured, so the bot's
    /// pre-sized calldata cannot over-spend the operation.
    /// Reverts (burning only gas) unless the USDC balance ends
    /// >= start + minProfit + 1.
    function liquidate(
        address account,
        address holder,
        address borrowMkt,
        address collateralMkt,
        address underlying,
        uint256 maxRepay,
        uint256 minProfit,
        address borrowPool,
        bytes calldata borrowSwapData,
        address sellPool1,
        bytes calldata sellSwapData1,
        address sellPool2,
        bytes calldata sellSwapData2
    ) external returns (uint256) {
        require(msg.sender == OWNER, "ONLY_OWNER");
        require(!inFlight, "BUSY");
        require(minProfit > 0, "MIN_PROFIT_ZERO");
        // Accrue the borrow and collateral markets INSIDE this transaction,
        // as the winner tx 0xf0579b9d did (frames: accrueInterest on mAERO
        // and mUSDC, then borrowBalanceStored, then the 0xf5e3c462 entry).
        // Same-transaction accrual makes borrowBalanceStored the principal
        // AT EXECUTION, so the halfBorrow cap below is computed on the
        // execution-time principal; a bot-side accrue tx one block earlier
        // leaves stored one block of interest behind that principal.
        IMToken(borrowMkt).accrueInterest();
        if (collateralMkt != borrowMkt) IMToken(collateralMkt).accrueInterest();
        uint256 balBefore = IERC20(USDC).balanceOf(address(this));
        collBefore = IERC20(collateralMkt).balanceOf(address(this));
        (uint256 lensErr, uint256 liquidity, uint256 shortfall) = IComptroller(COMPTROLLER)
            .getAccountLiquidity(holder);
        // FIX 2026-11-10 run c0d41b40: the delegate ABI returns
        // (error, liquidity, shortfall) - the old binding read the ERROR
        // word into `liquidity` (always 0: the guard was vacuous) and sized
        // repay from the LIQUIDITY word (0 exactly when the account is
        // unhealthy -> repay 0 -> NOT_LIQUIDATABLE on time-accrued heads).
        // Size from the SHORTFALL word and require it positive: a healthy
        // account has shortfall 0 (INSUFFICIENT_SHORTFALL on the delegate
        // side anyway), an unhealthy one shortfall > 0.
        require(lensErr == 0 && liquidity == 0 && shortfall > 0, "NOT_LIQUIDATABLE");
        uint256 repay = shortfall / 2 / 1e12; // 1e18-USD -> USDC 6-dec units
        address borrowU = IMToken(borrowMkt).underlying();
        // Repay band: the mToken caps a liquidation repay at HALF the
        // execution-time principal (closeFactor 0.5) AND at the shortfall.
        // Size at half the SHORTFALL (the archived proof10 green sizing:
        // repay 59.62 USDC = half the 119.24 shortfall at the proven WADO
        // capture 53265095) and cap at half the principal.
        // The 2026-11-10 "exact half" band story was measured at the mAERO
        // capture-1 reset 55297681 where the lens finds the holder HEALTHY
        // at C-1 (liquidity +18.94 USD; lead 72 RESOLVED: the failing code 3
        // = INSUFFICIENT_SHORTFALL) - every bracket size {half+-323,
        // half-1USD, shortfall/2} was rejected there for the wrong reason,
        // the tight band never existed. The sweep22/proof22 LIQUIDATE_REJECTED
        // "at every size incl exactly half" at the proven capture is the
        // fork-head elapsed artifact: after a historical reset the borrow is
        // not in default until TWO mined blocks after the reset (archived
        // fork note: "at reset 53265094 the borrow is not yet in default
        // (Compound elapsed>1 flips with the mined block)") and those runs
        // mined only their deploy first. With fund+deploy mined first the
        // archived proof10 was green; sweep23 (scratch/mw-maero/sweep23.py)
        // re-proves success, NO_PROFIT guard and eligibility on the current
        // artifact with the reset+fund+deploy+send recipe.
        uint256 halfBorrow = IMToken(borrowMkt).borrowBalanceStored(holder) / 2; // principal/2 AT EXECUTION after the inline accrue above; 6-dec units for a USDC borrow
        if (repay > halfBorrow) repay = halfBorrow;
        if (repay > maxRepay) repay = maxRepay;
        require(repay > 0, "NOT_LIQUIDATABLE");
        if (borrowU != USDC) require(isPoolAllowed(borrowPool), "BORROW_POOL");
        require(underlying == USDC || isPoolAllowed(sellPool1), "SELL_POOL");
        if (sellSwapData2.length > 0) require(isPoolAllowed(sellPool2), "SELL_POOL2");
        inFlight = true;
        IMorpho(MORPHO).flashLoan(USDC, repay,
            abi.encode(borrowU, account, holder, borrowMkt, collateralMkt, underlying,
                       borrowPool, borrowSwapData, sellPool1, sellSwapData1, sellPool2, sellSwapData2));
        inFlight = false;
        // clear every allowance opened during the operation (fail safe)
        IERC20(USDC).approve(borrowMkt, 0);
        IERC20(USDC).approve(MORPHO, 0);
        if (borrowU != USDC) IERC20(borrowU).approve(borrowMkt, 0);
        uint256 balAfter = IERC20(USDC).balanceOf(address(this));
        // THE loss bound: strictly higher USDC balance than before.
        require(balAfter >= balBefore + minProfit + 1, "NO_PROFIT");
        uint256 profit = balAfter - balBefore;
        // Pay the profit out to the bot wallet IN THIS transaction (review
        // a50ef674 item 2, 2026-11-10: the watchdog and gate sweep count only
        // the bot wallet's native/USDC balances, so profit left inside the
        // executor counted as lost). The transfer is exactly the measured
        // delta the guard just approved - the executor returns to balBefore
        // USDC, retained non-USDC inventory stays owned inventory, and the
        // loss bound covers the complete action including the payout.
        IERC20(USDC).transfer(OWNER, profit);
        emit Liquidated(account, collateralMkt, repay, profit);
        // The measured USDC balance delta, returned so a paper eth_call sees the
        // exact profit of the simulated call (the loss bound and the return are
        // the same number - the bot's profit estimate is this delta, not a
        // heuristic ratio).
        return profit;
    }

    /// Morpho flash-loan callback (selector 0x31f57072). Fires only while an
    /// owner-authorized operation is active. Sells ONLY the newly seized
    /// collateral delta — never retained inventory — on the whitelisted pools;
    /// the pool pays the output side and calls back for the input side.
    function onMorphoFlashLoan(uint256 amount, bytes calldata data) external {
        require(msg.sender == MORPHO, "UNTRUSTED");
        require(inFlight, "NO_OP");
        (address borrowU, address account, address holder, address borrowMkt,
         address collateralMkt, address underlying, address borrowPool, bytes memory borrowSwapData,
         address sellPool1, bytes memory sellSwapData1, address sellPool2, bytes memory sellSwapData2) =
            abi.decode(data, (address, address, address, address, address, address,
                              address, bytes, address, bytes, address, bytes));
        // The borrow position is keyed on the HOLDER (the LiquidateBorrow
        // event's holder field), not the borrower-field smart wallet, which
        // holds zero balances — passing it seizes nothing.
        // The mToken repays in the BORROW market's underlying: when that is
        // not USDC, convert the flashed USDC to it on the armed borrow pool
        // and repay with the swap proceeds; the mToken caps the real repay to
        // half the borrow balance, so leftover underlying stays as inventory.
        uint256 borrowAmt = amount;
        if (borrowU != USDC) {
            uint256 uBefore = IERC20(borrowU).balanceOf(address(this));
            _setSwapAmount(borrowSwapData, amount);
            _armSwap(borrowPool, USDC, amount);
            (bool ok, ) = borrowPool.call(borrowSwapData);
            require(ok, "BORROW_SWAP_FAILED");
            require(!armedSwap && activeSwapPool == address(0), "BORROW_SWAP_NOT_SETTLED");
            borrowAmt = IERC20(borrowU).balanceOf(address(this)) - uBefore;
            require(borrowAmt > 0, "NO_BORROW_SWAP");
            // The mToken does NOT cap an over-sized repay: it REVERTS with
            // LIQUIDATE_SEIZE_TOO_MUCH once the repay passes the measured
            // seize cap. Bracket measured at reset 53786332 (the 2026-11-06
            // drought-end liquidation): the winner repaid 0.002946 WETH =
            // 7.75 percent of borrowBalanceCurrent 0.0379867 and seized 1
            // percent of the mUSDC collateral = repay/0.9 in value (tx
            // 0x7ae200e3, replayed gen 134); 46 percent (0.017546 WETH), 50
            // percent and a debt/10 - 1 ppm = 9.9999 percent repay ALL re-
            // verted (proof11 tx 0x8b46e2e0cbd64f413affef312f91e37c)
            // while the 7.75 percent winner did not: the cap is the cometary
            // maxProportion on the SEIZE VALUE (1 percent of the collateral),
            // not half the debt. Cap the repay at debt/16 = 6.25 percent -
            // measured-safe under the winner ratio, and this event's 6.25
            // percent repay seizes 0.8 percent of the collateral, under the
            // 1 percent value cap. A repay that would seize more than 1
            // percent of collateral can still revert (tight-collateral ac-
            // counts) - a lead, not a loss: the loss bound watches USDC.
            // The swap excess stays as unconverted inventory; sizing the
            // flash near the repay is the bot's job (see proof11 maxRepay).
            uint256 seizeCap = IMToken(borrowMkt).borrowBalanceStored(holder) / 16; // stored: liquidate() accrued this market inside the same tx above, so stored == principal AT EXECUTION (no accrue side effects from a view)
            seizeCap -= seizeCap / 1000000;
            if (borrowAmt > seizeCap) borrowAmt = seizeCap;
        }
        IERC20(borrowU).approve(borrowMkt, borrowAmt);
        // The repay band (measured 2026-11-10 run this session, aero2.py
        // bracket at the mAERO capture-1 reset 55297681): with a bot-side
        // accrueInterest() tx one block ahead, this entry returned code 3
        // with no state change for EVERY repay {half_stored+323, half_stored
        // (a few units over half at execution), half_stored-323,
        // half_stored-1USD, shortfall/2 = 9.47 USDC}. The winner tx 0xf0579b9d
        // (trace winner-trace-maero.json) accrued BOTH markets inside its own
        // tx, read borrowBalanceStored, and called this entry with
        // 323806972 = exactly half of the just-accrued 647613944 principal -
        // it passed and seized. So the entry wants the repay ON the exact
        // half of the execution-time principal; this contract accrues in the
        // same transaction above and sizes at stored/2, which is exact. The
        // mcbXRP winner (wrapper 0xb6af8c9a, repay 2133.000097 = half of a
        // 4266.000194 debt, proof21) confirms the band is the class-wide
        // pattern, not this capture's quirk; the pre-upgrade mWETH proof11
        // bracket (7.75 percent of debt passing, 46-100 percent reverting)
        // shows an older era capped at half without the floor.
        {
            (bool okp, bytes memory rep) = borrowMkt.call(
                abi.encodeWithSelector(bytes4(0xf5e3c462), holder, borrowAmt, collateralMkt));
            require(okp && rep.length >= 32 && abi.decode(rep, (uint256)) == 0, "LIQUIDATE_REJECTED");
        }
        // mToken.liquidateBorrow credits the seized collateral mToken balance
        // to msg.sender — the executor itself (the Unitroller delegate keeps
        // the external caller as msg.sender; an EOA winner sees it on its
        // wallet). Measure the delta on this contract; no allowance needed.
        uint256 seized = IERC20(collateralMkt).balanceOf(address(this)) - collBefore;
        require(seized > 0, "NO_SEIZURE");
        uint256 underBefore = IERC20(underlying).balanceOf(address(this));
        IMToken(collateralMkt).redeem(seized);
        if (underlying != USDC) {
            uint256 delta = IERC20(underlying).balanceOf(address(this)) - underBefore;
            require(delta > 0, "NO_REDEEM");
            // Sell the redeemed delta on pool1 (and optionally its token1
            // output on pool2 — the two-hop sale the measured winner used).
            // The input side is paid by the V3 callback (transfer), so
            // collateral is never approved to a pool.
            address midTok = address(0);
            uint256 midBefore = 0;
            if (sellSwapData2.length > 0) {
                midTok = _swap2InputToken(sellSwapData2);
                midBefore = IERC20(midTok).balanceOf(address(this));
            }
            _setSwapAmount(sellSwapData1, delta);
            _armSwap(sellPool1, underlying, delta);
            (bool ok1, ) = sellPool1.call(sellSwapData1);
            require(ok1, "SELL1_FAILED");
            require(!armedSwap && activeSwapPool == address(0), "SELL1_NOT_SETTLED");
            if (sellSwapData2.length > 0) {
                uint256 mid = IERC20(midTok).balanceOf(address(this)) - midBefore;
                require(mid > 0, "NO_SELL1_OUTPUT");
                _setSwapAmount(sellSwapData2, mid);
                _armSwap(sellPool2, midTok, mid);
                (bool ok2, ) = sellPool2.call(sellSwapData2);
                require(ok2, "SELL2_FAILED");
                require(!armedSwap && activeSwapPool == address(0), "SELL2_NOT_SETTLED");
            }
            // intermediate-token dust is owned inventory; the loss bound only
            // concerns the USDC balance checked next in liquidate().
        }
        // Morpho pulls back exactly `amount` (no premium) after this returns
        IERC20(USDC).approve(MORPHO, amount);
    }

    function _armSwap(address pool, address payToken, uint256 payMax) private {
        armedSwap = true;
        activeSwapPool = pool;
        activePayToken = payToken;
        activePayMax = payMax;
    }

    // swapData layout (the pool.swap pattern proven on the fork by the
    // morpho-watcher-base executor): selector 4 bytes, then 5 head words
    // [recipient, zeroForOne, amountSpecified, sqrtPriceLimitX96, bytesOffset
    // 0xa0], then the bytes tail [length 0x40, token0, token1]: the callback
    // data. So the amount word occupies bytes [68:100) and the callback's two
    // addresses are at bytes [196:228) and [228:260).
    function _setSwapAmount(bytes memory data, uint256 amount) private pure {
        require(data.length == 4 + 8 * 32, "SWAP_DATA_LEN");
        // bytes memory stores the payload sequentially: selector at
        // bytes [0:4), recipient [4:36), zeroForOne [36:68), the
        // amountSpecified word at bytes [68:100). The length word
        // occupies data[0:32), so the payload starts at data+32.
        assembly ("memory-safe") {
            mstore(add(add(data, 32), 68), amount)
        }
    }

    // token that swap2 charges its input side = the intermediate token of the
    // two-hop sale: the pool token that is NOT USDC (the bot guarantees
    // exactly one of the two callback-data addresses is USDC).
    function _swap2InputToken(bytes memory data) private view returns (address) {
        (address t0, address t1) = abi.decode(slashSlice(data), (address, address));
        return t0 == USDC ? t1 : t0;
    }

    function slashSlice(bytes memory data) private pure returns (bytes memory) {
        require(data.length == 4 + 8 * 32, "SWAP_DATA_LEN");
        bytes memory tail = new bytes(64);
        for (uint256 i = 0; i < 64; i++) tail[i] = data[196 + i];
        return tail;
    }

    /// Uniswap V3 / Pancake V3 pool callback for direct pool swaps: the pool
    /// transferred the output token to us and is owed the input side.
    /// `data` = abi.encode(poolToken0, poolToken1) — the convention verified
    /// on the fork against the live pool (morpho-watcher-base executor, tx
    /// 0x2d56cc60: the pool calls uniswapV3SwapCallback(int256,int256,bytes),
    /// selector 0xfa461e33, with data abi.encode(USDC, cbZEC)). We pay the
    /// token whose delta is positive, so both pool orientations work
    /// (collateral may be token0 or token1). Router-style swaps do not call
    /// back and cannot be used with this executor.
    function uniswapV3SwapCallback(int256 amount0Delta, int256 amount1Delta, bytes calldata data) external {
        _payPool(amount0Delta, amount1Delta, data);
    }

    /// PancakeSwap V3 names the same callback pancakeV3SwapCallback.
    function pancakeV3SwapCallback(int256 amount0Delta, int256 amount1Delta, bytes calldata data) external {
        _payPool(amount0Delta, amount1Delta, data);
    }

    function _payPool(int256 amount0Delta, int256 amount1Delta, bytes calldata data) internal {
        require(inFlight && armedSwap, "INACTIVE_OP");
        require(msg.sender == activeSwapPool, "UNTRUSTED_POOL");
        (address token0, address token1) = abi.decode(data, (address, address));
        require(token0 == activePayToken || token1 == activePayToken, "BAD_TOKENS");
        if (amount0Delta > 0) {
            require(token0 == activePayToken && uint256(amount0Delta) <= activePayMax, "BAD_DELTA");
            IERC20(token0).transfer(msg.sender, uint256(amount0Delta));
        } else {
            require(token1 == activePayToken && amount1Delta > 0 && uint256(amount1Delta) <= activePayMax, "BAD_DELTA");
            IERC20(token1).transfer(msg.sender, uint256(amount1Delta));
        }
        armedSwap = false;
        activeSwapPool = address(0);
        activePayToken = address(0);
        activePayMax = 0;
    }

    /// Owner may withdraw accumulated profits. Principal at risk is bounded by
    /// liquidate()'s revert condition, not by sweep().
    function sweep(address token, address to, uint256 amount) external {
        require(msg.sender == OWNER, "ONLY_OWNER");
        IERC20(token).transfer(to, amount);
        emit Swept(token, to, amount);
    }
}
