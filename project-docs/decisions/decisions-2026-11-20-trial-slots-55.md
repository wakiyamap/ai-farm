# 試行の bot の live の枠を 50 本から 55 本に広げる（人間の判断 2026-11-20 昼）

`2026-11-20-trial-slots-50.md` の 1 だけを変えます。ほかの項目と `2026-11-20-trial-slots-45.md`、`2026-11-17-cheap-chain-trials.md` の条件はそのままです。

1. **同時に live に置く試行の bot は 55 本まで**。
2. 理由: 11-20 04:00 UTC の時点で 50/50 が埋まり、技術の審査を通って待っている bot が 3 本（trial-aave4-optimism、trial-aave4-avalanche、trial-folio-nav-base）あります。11-24 に締めるまでに、これらと、これから審査を通る bot も試したいからです。
3. 送信していない live の試行（nonce 1）を止めて入れ替えることはしません。試行は 7 日で締めるまで置いたままにします。
4. meta: paper-reviewer.md と builder.md の「50 本」を 55 本に直してください。
