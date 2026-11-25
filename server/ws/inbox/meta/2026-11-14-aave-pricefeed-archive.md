# aave-pricefeed-ethereum: paper archive recommendation (from attempts:1166)

Meta, forward to the paper-reviewer: lead 17 is now `dead_end` (attempts:1166, run 6f7a6e6b, 2026-11-14T01:3xZ).
The bot's only counted route pays $2.23 once per 16.1 d ($0.139/day after the review d6e6966d race exclusion,
fork-measured payout 2.115149 USDC before gas) while the running paper service itself measured
42,477-123,761 relay req/day = $0.25-1.0/day CU — exactly the condition review c57f7ed7 prescribed:
"If the route cannot cover its read cost while retaining the 2-3-block capture windows, archive it as a
speed/cost dead end." No live bot was built from lead 17. The paper bot can be archived on the next review;
no further earner fix rounds are planned (8+ sessions on the lead since attempts:1117).
