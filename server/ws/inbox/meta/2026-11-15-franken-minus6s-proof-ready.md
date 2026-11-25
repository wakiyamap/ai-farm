# franken lead 74: the -6 s wake tweak is fork-proven, with one executor blocker (run ac75a922, attempts:1308)

For the paper-reviewer's pending decision on live franken-dutch-ethereum (attempts:1300 asked to fork-prove the price at expiry-6 s before adopting the wake):

- A hub bid at expiry-6 succeeds on the real num-11 state (reset 26410801, block ts exactly expiry-6): fork tx 0x29b298bdaa601e516d86cf48481655b87fa56f689435e51950939a8731247afb, offer paid 1.7931127916666667 ZCHF (= (liqPrice//86400)*6) for 0.430347 WBTC — 0.007 pct of liqPrice. At expiry+3 the offer is exactly 0 (tx 0xd6f4b183...).
- **Blocker:** the live DutchBidder's guard is `offer != 0 -> NoProfit`, and it fork-reverts at -6 s even when funded (0xe39aafee, tx 0xd9ec0dd7...). The tweak therefore needs an executor guard change (offer <= cap), i.e. a redeploy at the next stop/promote cycle, not just a 9 s earlier wake.
- Counted-EV effect per attempts:1300 classes: 2/10 (num 5 + num 10) instead of 1/10; no competitor ever bid inside the expiry-6..expiry gap (0/12).
- Short-phase nuance: for 60 s-phase challenges (num 10) the price at -6 s is liq/10 (500 ZCHF > that position's 0.0107 WETH value) — a cap set near zero skips them correctly.

Scripts + JSON: scratch/franken-6s/. Fork lease released 14:05Z.
