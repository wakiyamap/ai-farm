# 試行の bot の live の枠を 70 本から 75 本に広げる（人間の判断 2026-11-22 未明）

`2026-11-21-trial-slots-70.md` の 1 だけを変えます。ほかの項目と `2026-11-20-trial-slots-45.md`、`2026-11-17-cheap-chain-trials.md` の条件はそのままです。

1. **同時に live に置く試行の bot は 75 本まで**。
2. 理由: 11-22 04:07 JST の時点で 69/70 です。審査を通って資金待ちの bot が 3 本（trial-dfm-pegkeeper-arbitrum、trial-behype-redeem-hyperevm、trial-hbhype-redeem-hyperevm）、審査待ちが 3 本（trial-lim-bsc、trial-kdiem-redeem-base、trial-swave-arb-polygon）あり、11-24 の締めまでに試したいからです。
3. 資金: Arbitrum の中間 wallet には人間が入金済みです（04:07 で 12.08 USD）。HyperEVM の中間 wallet にも人間が HYPE を入れます。入金が gate status に出るまでは、今までどおり資金不足の bot は promote しません。
4. promote の順: trial-dfm-pegkeeper-arbitrum を先に。あとは審査を通って資金が足りるものから順に。
5. meta: paper-reviewer.md と builder.md の「70 本」を 75 本に直してください。
