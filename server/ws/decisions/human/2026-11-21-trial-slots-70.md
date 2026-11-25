# 試行の bot の live の枠を 65 本から 70 本に広げる（人間の判断 2026-11-21 午後）

`2026-11-21-trial-slots-65.md` の 1 だけを変えます。ほかの項目と `2026-11-20-trial-slots-45.md`、`2026-11-17-cheap-chain-trials.md` の条件はそのままです。

1. **同時に live に置く試行の bot は 70 本まで**。
2. 理由: 11-21 14:13 JST の時点で 65/65 が埋まり、審査を通って待っている bot が 3 本あります（trial-uwinddown-base、trial-lim-bsc、trial-vtoken-arb-hyperevm）。11-24 の締めまでに試したいからです。
3. promote の順: **trial-uwinddown-base を先に**（wind-down vault の USDC が尽きると機会が消えるため。Base の中間 wallet には人間が入金します）。次に trial-lim-bsc。trial-vtoken-arb-hyperevm は builder が「同じ型を 4 時間前に小さすぎるとして閉じていた」と書いているので、reviewer の判断で置かなくてよいです。
4. meta: paper-reviewer.md と builder.md の「65 本」を 70 本に直してください。
