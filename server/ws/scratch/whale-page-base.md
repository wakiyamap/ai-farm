---
type: pitfall
chains: [base]
protocols: [moonwell_core]
author: paper-reviewer/gpt-6-sol
updated: 2026-11-10
---
# Moonwell whale captures: candidate coverage, cash starvation, and the seize quota

Conclusion (corrected 2026-11-10, review 872998e4): Moonwell `getAccountLiquidity` returns `(error, liquidity, shortfall)`. The third word is shortfall. The earlier claim below that the second word is shortfall was wrong; any capture-window or repay-scope conclusion here derived from the second word needs remeasurement. Some later probes already used the third word correctly. The bot's JavaScript decodes correctly, but the current moonwell-maero-base Solidity executor decodes incorrectly and reverts `NOT_LIQUIDATABLE` on a live underwater holder.

## getAccountLiquidity word order — corrected

At Base fork reset 53265094, the WADO capture holder `0x1a7c950a8fff56a7cc679b4cbd085f910c1e7234` returned `[0,189477497632080887558,0]` before the trigger (healthy) and `[0,0,593690901024254531217]` after two mined blocks (underwater). The current artifact's liquidation tx `0x05e900c0a9fda60530c87b7539cd63717fc22bd19bc3d41c4b592b44fc22de4d` reverted `NOT_LIQUIDATABLE` because `MoonwellWhale.sol` treats the middle zero as shortfall. At reset 55697122, mAERO holder `0x48768c348525b888e53232bc2d020eba94741255` returned `[0,1818657008811822247,0]`, meaning $1.818657 of liquidity and zero shortfall; README/manifest/proof22 had called it poll catchable. Use the third word for shortfall. See `bots/paper/moonwell-maero-base/review.md` (run 872998e4) and `scratch/review-872998e4494e4998b2cd87944e631f82/repro.py`.

## Whale capture classes (fork + ledger census, attempts 630-644)

- mcbXRPL collateral (0xb4fb8fed5b3aaa8434f0b19b1b623d977e07e86d): whale captures (54167202 repay 2750.87, 54911221 2133.06, 54922327 10955.96 USDC) were first read as "liquidatable only INSIDE the capture block (shortfall 0 at capture-1)" (attempt 630) - CORRECTED 2026-11-10: the capture-1 resets measure shortfall 312.59 / 109.74 / 177.58 USD with the correct word order (attempts 765, 768), and the fork REPLAY of the winner tx from the capture-1 pre-state SUCCEEDS (attempt 766, proof18 replay status 1), so the window is not same-block-only. What no plain caller can do there is liquidate at all: see the next section.
- mcbBTC collateral (0xf877acafa28c19b96727966690b2f44d35ad5976): holder 0x470bac04 oscillated healthy in every end-of-block probe; market getCash 140 -> 4 raw cbBTC until mid-capture-block (0.053 cbBTC arrived inside the capture block, 49x below the 261,279,421-raw whale seize): redeemable cash arrives only mid-block -> NO_REDEEM at every pre-capture reset, blocked_infra (attempt 633).
- mEURC collateral (0xb682c840...): poll window positive (borrower 0xbf65b647 liquidatable >=60 blocks before its captures 53462692/53464103/53517746) but market cash at capture-1 measured 0 / 0.014 / 1.855 EURC - cash-starved; the extended executor (7-arg constructor, P3 = EURC/WETH fee100 pool 0x4dbdcb087992404ea9b14fa83cc695b02797f39a) reverts NO_REDEEM at reset 54158850 (attempt 634). Open question for the next mEURC capture: cash < seize, or the borrower's post-seize remaining mToken balance < the redeem input - instrument getCash + balanceOf in scratch/mw-whale/proof15.py.
- mAERO borrow: all captures are one borrower, dead_end (attempt 638).
- mUSDC-borrow + mWADO-collateral (the bot's fully supported combo): its first whale captures came 2026-11-08 - block 54922711 repay 82.43 USDC (borrower 0xdedc8073...a92832), 54922713 repay 24.47 USDC (0x1537eab3...87c261). Fork reset probes 54922500-54922710 (run 651f5a54, corrected decode): both borrowers were UNDERWATER (shortfall 110.37 / 19.79 USD stable, margin 0) at every probed block up to capture-1: window >=211 blocks, poll-catchable. They were missed because both are first-time defaults (exactly ONE lifetime ledger event each = their own capture; ledger retention floor block 53247461) = invisible to the bot's event-marked repeat-default candidate premise (attempt 644).

## The mUSDC liquidation entries: a plain caller never liquidates the mcbXRP captures (run 5fe5f1e7, attempt 774)

On mUSDC (0xedc817a2) the compound-style entry `0x9d9ebc2a` REVERTS with empty data at the mcbXRP capture resets (it is not the delegate entry the winners use), and the delegate/propagate entry `0xf5e3c462` - the mainnet winners' selector, same (borrower, repay, collateralMarket) argument shape - returns code 3 with NO state change from a funded+approved PLAIN caller at every repay size bracketed at reset 54911220 (300/312/313/625/1100/2133.000097/2750e6 USDC; the winner-repay send 0x277ec7410ba384652cc466092fd6fb0cbbe5993f849cb5aeeeda43b40f9346fd: status 1, gas 350446, USDC delta 0.00, mcbXRP credit 0) and at the end-of-capture reset 54911221. The winners' trace shows the identical call from their executor INSIDE a Morpho flashLoan callback (EOA 0x0d35bdf9 -> router 0x2c7e9379 -> Morpho 0xbbbbbb... -> callback -> executor 0xb6af8c9a), and the protocol repo (moonwell-fi/moonwell-contracts-v2, main) tests a Chainlink OEV Morpho wrapper ALLOWLIST (test/unit/ChainlinkOEVMorphoWrapperAllowlistUnit.t.sol). The mcbXRP leg's failure is therefore a CALL-CONTEXT gate (new-debt propagation band / wrapper allowlist), not repay sizing and not an oracle window: reproduce the Morpho-flash callback caller on the fork before extending the executor, else this leg stays watch_only.

## First-time defaults vs repeat defaults

The bot marks candidates only from past LiquidateBorrow events on the 17 emitting markets. A first-time-default capture (no prior event) is structurally invisible until AFTER it happens; only re-default recaptures are trackable, and that path is fast: 0x470bac04 was detected 15 s after its first dust event (54922847) and recaptured 21 minutes later at repay 3615.70 USDC (54958965, collateral mcbBTC stayed watch-only). Fix candidate: seed the candidate set at startup from historical LiquidateBorrow borrowers (one-time historical getLogs scan, ~910 pages from the ledger floor block) so pre-deploy captured borrowers become trackable for re-default.

## The seize quota: fresh-account fork measurement (run 651f5a54, attempt 644)

At fork reset 54795793 (capture-1 of borrower 0x21df358f: mWETH borrow principal 3.504e16 raw, shortfall 75.94 USD, mUSDC collateral 11.49 units = 59.006 USDC), calling liquidateBorrow(address,uint256,address) on the BORROW MARKET 0x628ff693... (selector 0xf5e3c462; on the comptroller the same call reverts with empty data):

- repay 0.002190213698638597 ETH (= borrowBalanceCurrent/16, exactly the bot's flash sizing, ~$4.6-5.2) -> reverts LIQUIDATE_SEIZE_TOO_MUCH. This reproduces the bot's log: 17,701 of its 17,884 sims reverted this way (8,941 of them post-date its own 54795794 capture, shortfall_usd 0, quota then ~0), zero successes, candidate dropped as bad_debt 2.5 days later.
- repay 0.001137480828993648 ETH - the winner's ACTUAL repay at block 54795794 (ledger) -> SUCCESS on the fresh account. The quota accepted half the bot's sizing.
- repay = full borrowBalanceCurrent 0.0035043419178217562e18 also returned success once - non-monotonic against the debt/16 revert and NOT re-verified (principal clamping and the fund-token-from-the-market side effect are unseparated); the next session should bisect the 0.001137-0.003504e18 boundary on fresh resets and derive the quota formula.

Recipe: fund the caller with fork fund-token FROM the mWETH market account (0x628ff693... holds WETH reserves), approve the BORROW MARKET on WETH, call the borrow market. Do not fund through the comptroller.

## Remaining unmeasured direction

Borrow-side EURC whales (54697042 repay 86.61 EURC seize 753.37 mTokens; 55046981 repay 66.14 EURC by the repeat-default 0x33a7ec10, re-defaulting daily, tracked watch-only): the executor's borrow swap is USDC->WETH only; an EURC repay leg (Morpho EURC flash or USDC->WETH->EURC two-leg on the constructor P3) is unmeasured (attempt 643).

## The 14-day whale window of the resubmission has no supported-collateral capture (run 3240e1b4, attempt 923)

Ledger moonwell_core.liquidate_borrow[_ext] blocks 55512916-56090651 (50 events): only 2 captures repay >= 10 USD, and both sit on WATCH-ONLY collateral - 55648813 (repay 160.04 USDC, collateral mcbXRP, window >= 65536 blocks per attempt 922; re-enable needs a success proof WITH the Morpho-flash callback caller of the section above, not a plain caller) and 55717319 (repay 52.06 USDC, collateral market 0xd64bcb70c613a6d1f4d7d57ba64bb4a0767a9682 whose underlying() is the 2,968-byte Unit adapter 0xacfe6019ed1a7dc6f7b508c02d1b04ec88cc21bf - symbol() and decimals() REVERT on the adapter, pin markets through underlying(), not ERC20 getters). The executor-supported collateral markets (mWETH/mWADO/mUSDC) captured only sub-whale dust in the window (largest 5.38 USD repay) - moonwell-whale2-base has 0 executable natural captures in its own 14-day census window. Two USDC-collateral markets coexist on moonwell core: the bot's mUSDC 0xedc817a2 pays bridged USDC 0x833589fcd6edb6e08f4c7c32d4f71b54bda02913 (underlying() measured 2026-11-11), while the 40-capture collateral market 0xdc7810b47eaab250de623f0ee07764afa5f71ed1 underlying() = the legacy Base native USDC 0xa88594d404727625a9437c3f886c7643872296ae - the executor supports only the former.
