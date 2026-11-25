# 試行の bot の live の枠を 45 本から 50 本に広げる（人間の判断 2026-11-20）

`2026-11-20-trial-slots-45.md` の 1 だけを変えます。ほかの項目（並んでいる bot はすぐ promote、清算以外が先、wallet が足りなければ promote せず知らせる、技術の審査済みならどちらの reviewer が promote してもよい、Alchemy は 11-24 まで使い切ってよい）と、`2026-11-17-cheap-chain-trials.md` の条件はそのままです。

1. **同時に live に置く試行の bot は 50 本まで**。
2. 理由: 11-20 朝の時点で 45/45 が埋まり、技術の審査を通って待っている bot が 4 本（trial-dolomite-arbitrum、trial-llamalend-arbitrum、trial-silo1-liq-arbitrum、trial-aave4-optimism）、審査待ちが 1 本（trial-aave2-avalanche）あります。11-24 に締めるまでに、これらも live で試したいからです。
3. arbitrum の中間 wallet には人間が入金します。入金が確認できたら、arbitrum の 3 本も審査を通った順に promote してください。
4. meta: paper-reviewer.md と builder.md の「45 本」を 50 本に直してください。
