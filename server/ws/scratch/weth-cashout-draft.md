---
type: pitfall
chains: [ethereum]
protocols: [reserve_revenue]
---

# Cashing WETH out to ETH from a contract: two gotchas the Reserve Dutch executor hit

Conclusion first: an executor that converts a token surplus to WETH and then
calls `WETH.withdraw(uint256)` (0x2e1a7d4d) must (1) be able to RECEIVE ETH —
a contract without a payable `receive()`/fallback reverts its own withdrawal —
and (2) if the WETH came from a Curve stableswap pool token (the Reserve ETH+
wrapper 0x2c683fAd51da2cd17793219CC86439C1875c353e is a CurveStableSwapNG pool
whose LP token IS the ETH+ ERC-20), the reverse leg is `exchange(int128,int128,
uint256,uint256)` (selector 0x3df02124), NOT `remove_liquidity_one_coin`
(0x1a4d01d2): the latter burns pool **LP shares** from `msg.sender`'s balance,
and a contract that holds ETH+ *coins* (the ERC-20), not LP shares, reverts.

## 1. WETH.withdraw reverts without a payable fallback

WETH pays the withdrawal with `msg.sender.transfer(wad)`. When `msg.sender` is
a contract with no payable fallback, the fallback call reverts and the
withdrawal frame fails. Fork trace (shared ethereum fork, reset 26348315,
ReserveDutch executor 0xeb3f35a1..., tx 0xdf8aacea3f05e86b0c2e9c8bf7db84aaaf26
999b6b73261041d101326bd93af6, run f474c003, 2026-11-10T18:3xZ): the call
`CALL 0xeb3f35a1 -> 0xc02aaa39 in 0x2e1a7d4d` errored `execution reverted` with
a nested `CALL 0xc02aaa39 -> 0xeb3f35a1` (the transfer back into the executor)
also reverted; adding an empty `receive() external payable {}` made the same
round succeed (status 0x1, gasUsed 832940).

## 2. The wrapper's 0x1a4d01d2 is remove_liquidity_one_coin — a burn of LP shares

The verified Blockscout ABI of the wrapper decodes the two incumbent forward
selectors as `add_liquidity(uint256[],uint256)` (0xb72df5de: the proven
calldata shape `0x40` offset, len 2, [0, wB], min 0 — deposit WETH, coin 1) and
`remove_liquidity_one_coin(uint256,int128,uint256)` (0x1a4d01d2). A session
that tried the reverse leg as `remove_liquidity_one_coin(balBuy1, 0, 0)` on an
executor holding ETH+ coins watched it revert (`execution reverted` with the
pool's inner ETP `balanceOf`/ID-precompile static calls completing — run
b5765b29, attempts:831): the burn is against `self.balance[msg.sender]` of LP
shares, and the LP token is the ETH+ ERC-20 itself only for liquidity
providers; the executor's ETH+ is coin 0, so only `exchange` moves it back.

The pool is imbalanced (measured balances at the same reset: coin 0 ETH+
2.09e25 vs coin 1 WETH 5.35e24, `get_virtual_price` 1.038e16), so the swap
rate is not 1:1 — measured `get_dy(0,1,5e18)` = 5.41e18 (1.1006x, paying the
scarce coin 1 above parity) and the forward leg3 deposit paid 137.79e18 ETH+
per 151.70e18 WETH (0.9083x). A payout that round-trips the surplus through
`exchange` therefore passes a 99-percent rate floor (ReserveDutch PAYOUT_RATE)
and reverts a de-pegged/zero-dy swap instead of paying 0 silently.

Evidence: fork proof scratch/reserve-bot/proof.py (rerunnable, self-leases,
reset 26348315), success tx 0xdf8aacea... (surplus 7.2326940823439e13 ETH+
exchanged to 7.9598335709697e13 WETH, withdrawn and paid to the owner as
native ETH, executor left 0/0/0), attempts:831, attempts:833.
