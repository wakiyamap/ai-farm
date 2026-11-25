---
type: pitfall
chains: [base]
protocols: [moonwell_core]
author: earner/qwen3.8-flash-next
updated: 2026-11-09
---

# Moonwell whale captures: every measured whale class is poll-uncatchable or cash-starved

Conclusion: for moonwell-whale-base (15 s poll, atomic flash->liquidate->redeem->sell executor on Base), every whale capture (repay >= ~23 USD, the bot's profit floor at a 6.57 pct realized margin) measured so far belongs to a class the poll cannot win. Record this before planning another coverage round.

Measured classes (all fork/ledger-census, run ids in attempts 630-643):

- mcbXRPL collateral (mToken 0xb4fb8fed5b3aaa8434f0b19b1b623d977e07e86d): three whale captures (54167202 repay 2750.87, 54911221 2133.06, 54922327 10955.96 USDC) crossed to liquidatable only INSIDE the capture block (getAccountLiquidity shortfall 0 at capture-60 AND capture-1, fork probes). Chainlink price-cross default = same-block race. blocked_infra (attempt 630).
- mcbBTC collateral (0xf877acafa28c19b96727966690b2f44d35ad5976): holder 0x470bac04 oscillated healthy in every end-of-block probe up to its captures (54922895/54958964 liquidity +18.97 to +222 USD), market getCash 140 -> 4 raw cbBTC until mid-capture-block (5,329,126 raw = 0.053 cbBTC arrived only inside the capture block, 49x below the whale's 261,279,421-raw seize). Redeemable cash arrives only mid-block: NO_REDEEM at every pre-capture reset. blocked_infra (attempt 633).
- mEURC collateral (0xb682c840...): the poll window IS positive (borrower 0xbf65b647 liquidatable >=60 blocks before its captures 53462692/53464103/53517746), but market cash at capture-1 measured 0 / 0.014 / 1.855 EURC against the needed seize - cash-starved same-block class; the extended executor reverts NO_REDEEM at reset 54158850 with 1.86 EURC cash (attempt 634). Open question left for the next mEURC capture: whether cash < seize or the borrower's post-seize remaining mToken balance < the redeem input (dust captures fully liquidate small balances) - instrument getCash + balanceOf in scratch/mw-whale/proof15.py.
- mAERO borrow: coverage dead_end - all captures belong to one borrower (attempt 638).
- The fully supported combo (mUSDC borrow + mWADO collateral) finally got whale captures on 2026-11-08: block 54922711 repay 82.43 USDC (borrower 0xdedc8073...a92832) and 54922713 repay 24.47 USDC (0x1537eab3...87c261). Fork getAccountLiquidity (return (liquidityShortfall, liquidityMargin, liquidityUsed), selector 0x5ec88c79...) shows BOTH healthy until capture-1: shortfall 0, margin 110.37 / 19.79 USD stable from 211 blocks back through capture-1 (resets 54922500-54922710, run 651f5a54). Window 0 blocks: same-block class per decisions/human/2026-11-06-no-latency-race (attempt 642).

Two systemic notes for anyone extending the candidate set:

1. Event-marked candidates miss first-time defaults. The bot marks candidates only from past LiquidateBorrow events on the 17 emitting markets; both 11-08 WADO borrowers have exactly ONE lifetime ledger event (their own capture; ledger retention floor block 53247461). A first-time-default capture is structurally invisible until after it happens; only re-default recaptures are trackable. The recapture path is fast: 0x470bac04 was detected 15 s after its first dust event (54922847) and recaptured 21 minutes later at repay 3615.70 USDC.
2. Repay above the 50 pct quota reverts LIQUIDATE_SEIZE_TOO_MUCH. A boundary account (shortfall 75-78 USD, collateral nearly seized) reverted 10,710 consecutive 15 s simulations of the executor's debt/16 flash sizing (5.18 USDC repay, ~5.5 USD seize against a ~0.5x-50 pct collateral-balance quota) until dropped as candidate_drop_bad_debt; total sims 11-05..11-08: 17,884, all reverted (17,701 LIQUIDATE_SEIZE_TOO_MUCH, 183 NO_SEIZURE), zero successes. Quota-fit sizing (clamp the repay under CloseFactor x the borrower's current collateral value) is the untested candidate-side fix.

Remaining unmeasured direction: borrow-side EURC whales (54697042 repay 86.61 EURC seize 753.37 mTokens; 55046981 repay 66.14 EURC by the repeat-default 0x33a7ec10) - the executor's borrow swap is USDC->WETH only; an EURC repay leg (Morpho EURC flash or USDC->WETH->EURC on the constructor P3 pool) is unmeasured (attempt 643).
