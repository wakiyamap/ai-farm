// SPDX-License-Identifier: MIT
pragma solidity 0.8.17;

/// Field order must match the deployed Blend's stored Lien encoding exactly (Blend stores only
/// keccak256(abi.encode(lien)) per lienId and reverts InvalidLien unless the calldata struct
/// re-encodes to the stored hash - _validateLien in the verified Blend source).
/// Order pinned from the real winner calldata of tx
/// 0x9ed2ebfdf9f48b84f1eac8179adcd8a65f71240ccaae30f240e6f05e4af2805a (block 26389939), words 0-8:
/// lender, borrower, collection, tokenId, amount, startTime, rate, auctionStartBlock, auctionDuration.
/// The compiler version matters: this file must be compiled with solc 0.8.17, the same version as
/// the deployed Blend, because solc <= 0.8.17 hashes a struct function parameter in TUPLE form -
/// refinanceAuction((address,address,address,uint256,uint256,uint256,uint256,uint256,uint256),
/// uint256,uint256) = selector 0xa49c04be (measured from the winner tx input) - while solc 0.8.24
/// hashes the same signature FLATTENED (0xcf5da407): Blend's dispatcher then reverts every call
/// in its default at ~236 gas. The calldata layout of both forms is identical; only the hash differs.
struct Lien {
    address lender;
    address borrower;
    address collection;
    uint256 tokenId;
    uint256 amount;
    uint256 startTime;
    uint256 rate;
    uint256 auctionStartBlock;
    uint256 auctionDuration;
}

interface IBlend {
    function refinanceAuction(Lien calldata lien, uint256 lienId, uint256 rate) external;
}

/// The Blur Pool token (name "Blur Pool", 18 dec) is a 1:1 native-ETH accounting token verified at
/// 0x01a656024de4B89e2D0198BF4D468E8fd2358b17: deposit() is PAYABLE and mints msg.value 1:1 to
/// msg.sender; withdraw(amount) burns and pays native to the caller; balanceOf is the standard
/// selector; there is no approve, no ERC20 transfer, and transferFrom is callable only by the four
/// counterparties (Exchange, ExchangeV2, Swap, Blend) - Blend moves the debt and the repayments for
/// us, so the executor needs no approvals at all. No WETH anywhere: pool units are ETH 1:1.
interface IPool {
    function deposit() external payable;
    function withdraw(uint256 amount) external;
    function balanceOf(address account) external view returns (uint256);
}

/// Executor for the Blur Blend Dutch refinance-auction taker bot (lead 148).
/// The bot's float is held in the Blur Pool token (0x0000000000A39bb272e79075ade125fd351887ac):
/// receive() mints the native it receives 1:1 into Pool units. take() pays the current debt of an
/// open Dutch auction lien (Blend pulls Pool units from this contract with transferFrom - no
/// allowance, no approval) and becomes the lien lender at a rate we choose (over the Dutch ceiling
/// reverts RateTooHigh inside Blend; a stale lien tuple reverts InvalidLien; a closed auction
/// reverts AuctionIsNotActive). sweep() sends the Pool balance above the funded float (the accrued
/// interest after the lien met its next liquidity event - measured Repay/Refinance transfers arrive
/// from the borrower to this contract) to the bot wallet as native in one transaction.
/// Worst case per transaction is gas only; every unexpected state reverts the whole call.
contract BlurRefiTaker {
    error NotOwner();
    error LienTaken(uint256 lienId);
    error NoClaim(uint256 lienId);
    error TakeTooHighDebt(uint256 delta, uint256 debtCap);
    error SweepUnderwater(uint256 balance, uint256 funded);
    error SweepNoProfit(uint256 profit);

    IPool public immutable pool;
    IBlend public immutable blend;
    address public owner;

    uint256 public funded; // cumulative native received via receive() and minted into the float
    uint256 public withdrawing; // >0 only while sweep withdraws: the native the Pool pays back to
                                // this contract must NOT be re-minted by receive() (proven on fork
                                // run e80ea7d3: re-minting left the payout call with 0 balance and
                                // it died "insufficient balance for transfer")
    struct Claim { uint256 debt; uint256 rate; uint256 ts; bool active; }
    mapping(uint256 => Claim) public claims;
    uint8 public outstanding; // at most one lien taken at a time (watchdog: parked debt counts as loss)

    constructor(address pool_, address blend_) {
        owner = msg.sender;
        pool = IPool(pool_);
        blend = IBlend(blend_);
    }

    /// Fund the float: the bot wallet sends its native here; every wei is minted into Pool units 1:1.
    /// While sweep is withdrawing (withdrawing > 0) the Pool's own repayment of native lands here
    /// too and must pass through UNminted, so sweep can forward it to the wallet.
    receive() external payable {
        if (withdrawing == 0) {
            funded += msg.value;
            pool.deposit{value: msg.value}();
        }
    }

    /// Fork-only repayment simulation: the real venue pays accrued debt as Pool units (Blend's
    /// transferFrom from the borrower) without touching the funded float; on the fork a repayment
    /// is any native this contract mints without counting it as funded. Never used by the bot live.
    function mint() external payable {
        pool.deposit{value: msg.value}();
    }

    /// Take an open refinance auction: pays the full current debt in Pool units, becomes the lien
    /// lender. debtCap must equal the reconstructed current debt (amount + accrued) - a bigger
    /// on-chain payment reverts the take (TakeTooHighDebt), so a wrong reconstruction can never overpay.
    function take(uint256 lienId, Lien calldata lien, uint256 rate, uint256 debtCap) external {
        if (msg.sender != owner) revert NotOwner();
        if (claims[lienId].active) revert LienTaken(lienId);
        require(outstanding < 1, "one lien at a time");
        uint256 bal0 = pool.balanceOf(address(this));
        blend.refinanceAuction(lien, lienId, rate);
        uint256 delta = bal0 - pool.balanceOf(address(this));
        if (delta > debtCap) revert TakeTooHighDebt(delta, debtCap);
        require(delta > 0, "debt paid");
        claims[lienId] = Claim(delta, rate, block.timestamp, true);
        outstanding += 1;
    }

    /// After a measured Repay/Refinance on our taken lien: debt plus accrued interest came back to
    /// this contract as Pool units, so the Pool balance is at least the funded float again; the
    /// excess is the realized interest profit, withdrawn from the pool as native and sent to the
    /// bot wallet in the same transaction.
    function sweep(uint256 lienId, uint256 minProfit) external {
        if (msg.sender != owner) revert NotOwner();
        if (!claims[lienId].active) revert NoClaim(lienId);
        uint256 bal = pool.balanceOf(address(this));
        if (bal < funded) revert SweepUnderwater(bal, funded);
        uint256 profit = bal - funded;
        if (profit < minProfit) revert SweepNoProfit(profit);
        claims[lienId].active = false;
        outstanding -= 1;
        if (profit > 0) {
            withdrawing = 1;
            pool.withdraw(profit); // Pool units -> native to this contract, 1:1 (receive() gated)
            withdrawing = 2; // keep the gate over the payout call: the native stays ours, not the Pool's
            (bool ok, ) = payable(owner).call{value: profit}("");
            withdrawing = 0;
            require(ok, "native payout");
        }
    }
}
