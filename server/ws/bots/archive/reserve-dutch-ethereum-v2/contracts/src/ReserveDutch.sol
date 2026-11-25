// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

// ReserveDutch: atomic Reserve revenue Dutch-auction executor (ETH+ trader route).
// Entry bidDutch calls trade.bidWithCallback(empty bytes): the trade sends the
// lot (weETH) here and calls dutchTradeCallback(buyToken, bid, data). We sell
// the lot over the incumbent-proven direct-call route (attempt 223, fork trace
// of fill 0xe80e2583; no router, every leg a direct call from this contract):
//   leg1 weETH unwrap:  CALL 0xde0e9a3e(uint256) on weETH -> eETH
//   leg2 swapX:         CALL 0x6c08c57e(eETH, WETH, amountIn, 0, recipient) on 0x68025a46 -> WETH
//   leg3 ETH+ wrapper:  CALL 0xb72df5de(0x40, 0, 2, 0, depositAmount) then
//                       CALL 0x1a4d01d2(amount, 0, 0) on 0x2c683fad -> ETH+
// leg3Variant pins the dynamic bindings proven by the fork harness. Then we
// repay the dutch bid to the trade from the proceeds. Reverts unless the
// buy-token delta after repayment is >= minProfitBuy (NO_PROFIT) and every
// sell-side token was fully consumed (RESIDUAL). Gas is paid by the owner's
// wallet; after the NO_PROFIT check bidDutch CONVERTS the buy-token surplus
// back to ETH and pays it to the owner in the SAME transaction: human
// decision 2026-11-11-executor-bots-funds item 3 counts only native and
// USDC in the bot wallet as funds (X / gate sweep / watchdog), so the
// payout legs are:
//   payout1 ETP -> WETH: approve ETP, then the pool's permissionless swap
//     leg CALL exchange(0, 1, balBuy1, 0) on 0x2c683fad (4-arg selector
//     0x3df02124; 5-arg receiver variant 0xddc1f59d pinned by payoutVariant)
//     - the pool pulls balBuy1 of coin 0 (ETH+) from us and pays coin 1
//     (WETH) to us. NOT remove_liquidity_one_coin: that burns pool LP
//     shares from msg.sender's LP balance (the LP token is the pool itself),
//     and our executor holds ETH+ coins, not LP shares (run b5765b29: the
//     0x1a4d01d2(bal,0,0) burn CALL reverted for our caller for exactly
//     this reason).
//   payout2 WETH -> ETH: CALL 0x2e1a7d4d(balWETH) on WETH (withdraw)
//   payout3 ETH out: owner.call{value: balance} (PAYOUT_SEND); the contract
//     has a payable receive() so the WETH.withdraw transfer is accepted
//     (a contract recipient without a payable fallback reverts WETH.withdraw)
// The payout rate floor (PAYOUT_RATE, WETH >= 99 percent of the ETP
// surplus) keeps a zero-dy or de-pegged swap from silently paying 0 ETH
// after the NO_PROFIT guard. A failed payout leg reverts the whole bid; the
// contract holds no surplus between trades and every successful bid pays
// its profit to the owner wallet atomically as native ETH.
//
// Inclusion-time gas-USD bound (review 279/attempt 272/7e653174 chain): the
// bidDutch entry reverts (GAS_USD) unless its own worst-case gas fee, valued
// at the on-chain Chainlink ETH/USD answer of the EXECUTION block (read at
// inclusion, freshness enforced on-chain: ORACLE_STALE), stays <= 20.00 USD.
// tx.gasprice is the effective gas price actually paid at inclusion (EIP-1559:
// base fee + priority fee, and <= maxFeePerGas of the signed transaction), so
// the ceiling (remaining gas + intrinsic slack) x tx.gasprice x answer is
// computed from transaction-included data AT INCLUSION, not at decision time.
// A successful bid therefore pays <= 20 USD of gas at the oracle price of its
// own execution block; a GAS_USD/ORACLE_* revert happens before any leg and
// pays <= 60000 x maxFeePerGas = 0.00012 ETH of gas (early revert). Absolute
// ETH bound stays signed: gasLimit x maxFeePerGas.

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address who) external view returns (uint256);
}

interface ITrade {
    function bidWithCallback(bytes calldata data) external returns (uint256);
}

interface IAggregatorV3V1 {
    function latestRoundData() external view returns (uint80 roundId, int256 answer,
        uint256 startedAt, uint256 updatedAt, uint80 answeredInRound);
}

contract ReserveDutch {
    address public owner;
    address public activeTrade; // trade currently mid-bid (callback caller)

    // ETH+ trader route constants (attempt 223 trace 0xe80e2583)
    address public constant WEETH = 0xCd5fE23C85820F7B72D0926FC9b05b43E359b7ee;
    address public constant EETH = 0x35fA164735182de50811E8e2E824cFb9B6118ac2;
    address public constant SWAPX = 0x68025A4615407993A680102b08a23A61D11C657C;
    address public constant WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address public constant ETP = 0xE72B141DF173b999AE7c1aDcbF60Cc9833Ce56a8; // ETH+
    address public constant ETPWRAP = 0x2c683fAd51da2cd17793219CC86439C1875c353e;

    // Inclusion-time gas-USD bound (see header): Chainlink ETH/USD mainnet
    // feed (decimals 8, 'ETH / USD'), 20.00 USD cap in micro-USD, staleness
    // cap in seconds (measured quiet-hour round gap 3624 s: consecutive rounds
    // updated 2026-11-06T09:13:11Z and 10:13:35Z through this relay — a quiet
    // stretch with no deviation trigger; the volatile-hours cadence 1236 s of
    // attempts 249/266 is the floor, not the cap. 3660 = 3624 gap + ~25 s
    // answer-delivery slack + margin; the old 2400 s cap failed closed
    // through every quiet hour, see attempt 281), and a gas slack
    // that covers the fixed intrinsic cost of this calldata-shaped call
    // (21000 + 68 + 4 x 100 <= 21468 < 22000).
    address public constant ETHUSD_AGG = 0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419;
    uint256 public constant MAX_GAS_USD_MICRO = 20000000;
    uint256 public constant MAX_ORACLE_AGE = 3660;
    uint256 public constant INTRINSIC_SLACK = 22000;

    uint256 public leg3Variant;
    uint256 public repayMode; // 0: repay bid via transfer in callback; 1: approve trade for bid, trade pulls at settlement
    uint256 public payoutVariant; // 0: pool exchange 4-arg (0x3df02124); 1: exchange 5-arg receiver variant (0xddc1f59d) - pinned by the fork proof
    uint256 public constant DUST = 1000; // swapX rounding dust per leg

    modifier onlyOwner() {
        require(msg.sender == owner, "NOT_OWNER");
        _;
    }

    // WETH.withdraw pays its ETH out with msg.sender.transfer: a contract
    // recipient without a payable fallback reverts the withdrawal (fork
    // trace run f474c003: CALL 0x2e1a7d4d on WETH reverted for exactly this
    // reason). Accept incoming ETH here; owner.call then drains it out.
    receive() external payable {}

    constructor(uint256 leg3Variant_, uint256 repayMode_, uint256 payoutVariant_) {
        owner = msg.sender;
        leg3Variant = leg3Variant_;
        repayMode = repayMode_;
        payoutVariant = payoutVariant_;
    }

    function _call(address target, bytes memory cd) internal {
        (bool ok, bytes memory res) = target.call(cd);
        require(ok, "LEG_REVERT");
        if (res.length > 0 && res.length < 32) require(false, "LEG_SHORT_RET");
    }

    function _callRet32(address target, bytes memory cd) internal returns (uint256) {
        (bool ok, bytes memory res) = target.call(cd);
        require(ok, "LEG_REVERT");
        require(res.length >= 32, "LEG_SHORT_RET");
        return abi.decode(res, (uint256));
    }

    /// @dev Entry: bids the current dutch price on `trade` (buy = ETH+ token),
    /// swapping the received weETH lot over the fixed route. minProfitBuy is
    /// our worst-case gas priced in buy units plus margin.
    function bidDutch(address trade, address buy, uint256 minProfitBuy) external onlyOwner {
        require(activeTrade == address(0), "BUSY");
        require(buy == ETP, "BAD_BUY");

        // Inclusion-time gas-USD bound: value our own gas ceiling at the
        // Chainlink ETH/USD answer of THIS execution block and require it to
        // stay <= 20.00 USD before bidding anything. entryGas is read before
        // any leg: everything this transaction consumes from here on is at
        // most entryGas, and the fixed intrinsic part of the signed call is
        // covered by INTRINSIC_SLACK, so (entryGas + slack) x tx.gasprice is
        // an upper bound of the fee this transaction will pay at inclusion
        // (tx.gasprice = the effective price actually charged, <= maxFeePerGas
        // signed into the transaction). feeWei x answer / 1e12 = micro-USD.
        uint256 entryGas = gasleft();
        (, int256 answer, , uint256 updatedAt, ) = IAggregatorV3V1(ETHUSD_AGG).latestRoundData();
        require(answer > 0, "ORACLE_ANSWER");
        require(block.timestamp > updatedAt && block.timestamp - updatedAt <= MAX_ORACLE_AGE, "ORACLE_STALE");
        uint256 feeWeiCeil = (entryGas + INTRINSIC_SLACK) * tx.gasprice;
        // wei(1e-18 ETH) x answer(1e8 USD) / 1e26 = USD; x1e6 = micro-USD:
        require(feeWeiCeil * uint256(answer) <= MAX_GAS_USD_MICRO * 1e20, "GAS_USD");

        activeTrade = trade;
        uint256 balBuy0 = IERC20(buy).balanceOf(address(this));
        uint256 balW0 = IERC20(WEETH).balanceOf(address(this));

        ITrade(trade).bidWithCallback(""); // triggers dutchTradeCallback

        activeTrade = address(0);
        require(IERC20(WEETH).balanceOf(address(this)) <= balW0, "RESIDUAL");
        require(IERC20(EETH).balanceOf(address(this)) <= DUST, "RESIDUAL");
        require(IERC20(WETH).balanceOf(address(this)) <= DUST, "RESIDUAL");
        uint256 balBuy1 = IERC20(buy).balanceOf(address(this));
        require(balBuy1 >= balBuy0 + minProfitBuy, "NO_PROFIT");
        // Pay the earned surplus out to the owner wallet INSIDE this same
        // transaction as NATIVE ETH (human decision 2026-11-11-executor-
        // bots-funds item 3: X / gate sweep / watchdog count only native
        // and USDC; value left as ETH+ in the wallet is not swept). The
        // NO_PROFIT guard above already required a gain of at least
        // minProfitBuy (which prices our worst-case gas) on balBuy1 -
        // balBuy0; the payout legs convert that buy balance to ETH and
        // drain it to owner, leaving the executor at 0 (buy balance, WETH
        // and native all drained; balBuy0 = 0 for every clean owner), and
        // any failed leg reverts the whole bid.
        require(IERC20(buy).approve(ETPWRAP, balBuy1), "PAYOUT_APPROVE");
        uint256 balW0p = IERC20(WETH).balanceOf(address(this)); // <= DUST above
        if (payoutVariant == 0) {
            // pool.exchange(0 -> 1, balBuy1, 0): the pool pulls balBuy1 of
            // coin 0 (ETH+) from us and pays coin 1 (WETH) to us
            _call(ETPWRAP, abi.encodeWithSelector(0x3df02124,
                int256(0), int256(1), balBuy1, uint256(0)));
        } else {
            // exchange receiver variant: exchange(0, 1, balBuy1, 0, this)
            _call(ETPWRAP, abi.encodeWithSelector(0xddc1f59d,
                int256(0), int256(1), balBuy1, uint256(0), address(this)));
        }
        uint256 balW1 = IERC20(WETH).balanceOf(address(this));
        // rate floor: WETH >= 99 percent of the ETH+ surplus (PAYOUT_RATE) -
        // a zero-dy or de-pegged swap reverting the bid beats a silent 0 ETH
        // payout after the guard
        require(balW1 - balW0p >= balBuy1 - balBuy1 / 100, "PAYOUT_RATE");
        _call(WETH, abi.encodeWithSelector(0x2e1a7d4d, balW1)); // WETH.withdraw
        (bool sent, ) = owner.call{value: address(this).balance}("");
        require(sent, "PAYOUT_SEND");
    }

    /// @notice DutchTrade callback: swap the received lot and repay the bid.
    function dutchTradeCallback(address buyToken, uint256 bid, bytes calldata data) external {
        require(msg.sender == activeTrade, "NOT_ACTIVE_TRADE");
        require(buyToken == ETP, "BUY_MISMATCH");
        require(data.length == 0, "BAD_DATA");

        // leg1: unwrap the weETH lot into eETH (burn-from-caller, incumbent pattern)
        uint256 lot = IERC20(WEETH).balanceOf(address(this));
        _call(WEETH, abi.encodeWithSelector(0xde0e9a3e, lot));

        // leg2: swapX direct eETH -> WETH (pulls eETH from us, pays WETH to us)
        uint256 eB = IERC20(EETH).balanceOf(address(this));
        require(IERC20(EETH).approve(SWAPX, eB), "APPROVE_EETH");
        _call(SWAPX, abi.encodeWithSelector(
            0x6c08c57e, EETH, WETH, eB, uint256(0), address(this)));
        require(IERC20(EETH).balanceOf(address(this)) <= DUST, "EETH_RESIDUAL");
        uint256 wB = IERC20(WETH).balanceOf(address(this));

        // leg3: WETH -> ETH+ on the ETH+ wrapper: deposit (pulls WETH) then
        // withdraw (pays ETH+), incumbent raw-call layouts, dynamic bindings
        // pinned by the fork harness.
        require(IERC20(WETH).approve(ETPWRAP, wB), "APPROVE_WETH");
        if (leg3Variant == 0) {
            // deposit pays out shares; withdraw the received shares exactly
            uint256 shares = _callRet32(ETPWRAP, abi.encodeWithSelector(
                0xb72df5de, uint256(0x40), uint256(0), uint256(2), uint256(0), wB));
            _call(ETPWRAP, abi.encodeWithSelector(0x1a4d01d2, shares, uint256(0), uint256(0)));
        } else if (leg3Variant == 1) {
            // withdraw by input amount (incumbent 1a4d01d2 arg = WETH in)
            _call(ETPWRAP, abi.encodeWithSelector(
                0xb72df5de, uint256(0x40), uint256(0), uint256(2), uint256(0), wB));
            _call(ETPWRAP, abi.encodeWithSelector(0x1a4d01d2, wB, uint256(0), uint256(0)));
        } else {
            // attempt-223 listing order: withdraw first, then deposit
            _call(ETPWRAP, abi.encodeWithSelector(0x1a4d01d2, wB, uint256(0), uint256(0)));
            _call(ETPWRAP, abi.encodeWithSelector(
                0xb72df5de, uint256(0x40), uint256(0), uint256(2), uint256(0), wB));
        }
        require(IERC20(WETH).balanceOf(address(this)) <= DUST, "WETH_RESIDUAL");

        // repay the dutch bid from the swap proceeds (principal-free route)
        require(IERC20(ETP).balanceOf(address(this)) >= bid, "PROCEEDS_LT_BID");
        if (repayMode == 0) {
            require(IERC20(ETP).transfer(msg.sender, bid), "REPAY_FAIL");
        } else {
            require(IERC20(ETP).approve(msg.sender, bid), "REPAY_APPROVE");
        }
    }
}
