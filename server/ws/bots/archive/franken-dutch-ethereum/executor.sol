// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IHub {
    function price(uint32 num) external view returns (uint256);
    function challenges(uint256 num) external view returns (address challenger, uint40 start, address position, uint256 size);
    function bid(uint32 num, uint256 size, bool postpone) external;
}
interface IZCHF {
    function transferFrom(address from, address to, uint256 wad) external returns (bool);
    function transfer(address to, uint256 wad) external returns (bool);
    function approve(address spender, uint256 wad) external returns (bool);
}
interface IToken {
    function balanceOf(address) external view returns (uint256);
    function transfer(address to, uint256 wad) external returns (bool);
}

/// One-transaction Dutch-challenge bidder for the frankencoin MintingHub.
/// The bot bids only after the hub's Dutch price has fully decayed (the hub price is
/// exactly 0 from start + 2 * phase on, measured from the verified hub source), so the
/// bid pays zero ZCHF. The contract enforces the gain for every accepted input: it
/// reverts unless the challenge still exists (NoChallenge), the hub offer
/// (hub.price(num) * sz / 1e18) is exactly 0 (NoProfit), the received collateral
/// delta equals the bid size sz >= 1 exactly (BadCollateralDelta), the payout
/// transfer to the owner succeeds (BadTransfer) and the owner's token balance delta
/// equals the gained size exactly (BadOwnerDelta). The whole action - the bid and the
/// payout to the bot wallet - is therefore ONE transaction through this contract, and
/// every accepted call ends with the owner holding strictly more collateral than
/// before it and zero ZCHF paid, whatever maxOffer the caller claimed: the worst case
/// is the transaction gas.
contract DutchBidder {
    IHub public immutable hub;
    IZCHF public immutable zchf;
    address public immutable owner;

    error NoChallenge();      // challenge gone or fully bid by others
    error NoProfit();         // hub Dutch price not fully decayed: the bid would pay ZCHF
    error BadCollateralDelta(); // received collateral differs from the bid size
    error BadTransfer();      // ERC-20 transfer of the gained collateral to the owner failed
    error BadOwnerDelta();    // owner balance delta differs from the gained collateral
    error NotOwner();

    constructor(address hub_, address zchf_) {
        hub = IHub(hub_);
        zchf = IZCHF(zchf_);
        owner = msg.sender; // the gate deploys the executor from the bot wallet, so owner = the bot wallet
        if (IZCHF(zchf_).approve(hub_, type(uint256).max)) {} // hub pulls the (zero) offer per bid
    }

    /// @param num challenge number from the ChallengeStarted event
    /// @param size desired collateral size (capped to the remaining challenge size)
    /// @param token collateral token (the gained delta is paid out and verified against it)
    function bid(uint32 num, uint256 size, address token) external {
        if (msg.sender != owner) revert NotOwner();
        (address challenger, , , uint256 csize) = hub.challenges(num);
        if (challenger == address(0x0)) revert NoChallenge();
        uint256 sz = size < csize ? size : csize;
        if (sz == 0) revert NoChallenge();
        uint256 offer = (hub.price(num) * sz) / 10 ** 18; // hub price decays with time only
        if (offer != 0) revert NoProfit(); // zero-payment strategy: pay nothing, take the collateral
        uint256 before = IToken(token).balanceOf(address(this));
        uint256 obefore = IToken(token).balanceOf(owner);
        hub.bid(num, sz, false);
        uint256 gained = IToken(token).balanceOf(address(this)) - before; // reverts on underflow
        if (gained != sz) revert BadCollateralDelta();
        if (!IToken(token).transfer(owner, gained)) revert BadTransfer(); // payout atomic with the bid
        if (IToken(token).balanceOf(owner) - obefore != gained) revert BadOwnerDelta();
    }

    /// Owner recovery for any collateral left in the executor (the normal path pays out
    /// inside bid; kept for stranded balances, with the ERC-20 return value checked).
    function sweep(address token, uint256 amount) external {
        if (msg.sender != owner) revert NotOwner();
        if (!IToken(token).transfer(owner, amount)) revert BadTransfer();
    }

    /// Owner withdraws any ZCHF left in the executor in a separate transaction.
    function sweepZCHF(uint256 amount) external {
        if (msg.sender != owner) revert NotOwner();
        if (!zchf.transfer(owner, amount)) revert BadTransfer();
    }
}
