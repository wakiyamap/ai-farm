# S の判断: rebase などでプールの reserve を超えた残高を取る型（skim 型）はしない（人間、2026-11-23）

inbox/human `2026-11-22-meta-s-ruling-rebase-skim.md`（meta 510ffa0f）への答えです。

1. **答えは「いいえ」**。rebase するトークンや送金手数料などで、プールの帳簿上の reserve より多く残った残高を、`skim`・`sellBase`・`swap` などで持ち出す型（uniswap-skim として知られている型）は、farm では取りません
2. 理由: その残高は本来 LP やプールのものです。プロトコルが「呼んだ人に払う」と決めた報酬ではなく、プールの会計が rebase を計上しないために漏れているだけです。S の「意図して誰にでも払う仕組み」に当たりません。11-22 の LBP / hLBP の件（pair の残高超過を `swap()` で持ち出す型）とも形が同じです
3. lead 415（Polygon の sLGNS / DODO）は dead_end にしてください。理由は「S: skim 型（2026-11-23 人間）」
4. 同じ型は今後も lead にしない、bot にしない。scout は見つけたら verdict を `unpaid` にして、attempts に「skim 型（S）」と 1 行残すだけにしてください
5. meta: wiki `methods/skim-excess-sweep.md` の「当たりが出たら判断をもらう」を、この判断（しない）に書き換えてください。builder.md・scout.md に 1 行ずつ足す場合は、プロンプトの大きさの上限を守ってください
