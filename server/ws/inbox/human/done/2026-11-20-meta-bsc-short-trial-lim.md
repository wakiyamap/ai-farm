# bsc の中間 wallet が約 3.3 USD 足りません（trial-lim-bsc）（meta 1162159c、2026-11-20 22:3xZ）

1. `trial-lim-bsc` は試行の審査を通り（`bots/paper/trial-lim-bsc/review.md`、paper-reviewer a9f8f418）、枠待ちです。`gate status`（22:2xZ）では試行の bot が 60/60 本 live で、枠が空いても bsc の中間 wallet は 6.81 USD の BNB しかなく、`capital_usd` 10 USD + executor の deploy ガス（約 0.03 USD）に約 3.3 USD 足りません。
2. お願い: bsc の中間 wallet に BNB を 5 USD ほど入れてください（入金は人間の判断です）。入金と枠の空きがそろえば paper-reviewer が `gate promote trial-lim-bsc` します。
3. 参考: ethereum の one-shot bot `oneshot-bundles-rebalance-ethereum`（Bundles.fi の rebalance の取り残し、fork で +30.8 USD 見込み、急ぎの審査）が要る約 30 USD の ETH は、ethereum の中間 wallet（196.1 USD）で足ります。入金は不要です。
