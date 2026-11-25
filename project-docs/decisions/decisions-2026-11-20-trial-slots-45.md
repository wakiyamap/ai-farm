# 試行の bot の live の枠を 30 本から 45 本に広げ、審査済みの bot を全部出す（人間の判断 2026-11-20）

`2026-11-18-trial-slots-30.md` の 1 を変えます。ほかの条件（1 本 20 USD 以下、1 回の送信の損 1 USD 以下、ethereum 以外、7 日で締める）はそのままです。

1. **同時に live に置く試行の bot は 45 本まで**。
2. 理由: 11-24 に全体を判断して締めます。それまでに、審査を通って並んでいる bot（11-20 01:00 JST の時点で 13 本）をすべて live で試したいからです。枠の残りは、これから審査を通る bot に使います。
3. **並んでいる bot はすぐに promote してください**。清算以外の型を先に、そのあとは審査を通った古い順です。毎回 `gate status` で、中間 wallet のそのチェーンの残高が capital と配備のガスに足りるかを確かめ、足りなければ promote せず inbox/human に「<チェーン> が <USD> 足りない」と書いてください（並びはそのまま）。
4. 技術の審査（fork の証明、manifest-check、executor の確認）がすでに済んで `wait (parked: approved ...)` になっている bot は、作り手と逆のモデルの決まりにかかわらず、paper-reviewer と paper-reviewer-claude のどちらが promote してもかまいません。promote は審査のやり直しではありません。
5. **Alchemy の月の枠は 11-24 まで使い切ってかまいません**。読み取りが足りないことを理由に測定や証明をあきらめないでください。meta は `/health` の `cycle` を見て、**11-24 より前に尽きそう**なときだけ inbox/human に知らせてください。
6. meta: paper-reviewer.md と builder.md の「30 本」を 45 本に直してください。
