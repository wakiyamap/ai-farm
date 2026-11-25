# 待機中の live bot 2 本の Alchemy 費用（meta から転送、2026-11-12）

元: inbox/meta/2026-11-12-waiting-fleet-read-cost.md（earner run 1ab3464d、attempts:1026）、inbox/meta/2026-11-12-waiting-watchers-feed-cheaper.md（attempts:1048）、inbox/meta/2026-11-13-waiting-bots-item2.md（attempts:1032）

## 判断していただきたいこと

decision 2026-11-12 項目 6 では「1 日約 1M CU を超える bot は人間の判断が必要」となっています。待機中の 2 本はこの規則より前（11-09）に promote されたため、まだ判断を受けていません。

| bot | 1 日の CU（実測） | USD/日 | 7 日の実現利益 |
|---|---|---|---|
| gearbox-v3-watcher-ethereum | 約 1.30M（20 秒ごとのポーリング、1 回 4 呼び出し） | 約 0.69 | 0（promote 後の送信 0 件） |
| franken-dutch-ethereum | 約 0.32M（60 秒ごと） | 約 0.17 | 0 |

live レーンは 11-12 の 21:52Z に 1.394M / 1.5M CU で、1 日の終わりには上限近くまで達する見込みです。

## 選択肢（earner の測定に基づく。どちらも gate の restart が必要で、earner や meta にはできません）

1. **gearbox: ポーリング間隔を 20 秒から 300 秒に延ばす**。過去に実測した捕捉の猶予は最短でも 34 ブロック（約 7 分、attempts 358）あるので、300 秒にしても間に合います。費用は約 14 分の 1（約 0.09M CU/日）になります。間隔は bot.js の定数（`CYCLE_MS`）です。
2. **franken: feed の `/logs` で `ChallengeStarted` を待つ形に変える**。イベントは約 43 日に 1 回、1 件約 760 バイトで約 30 CU です。安全のためのポーリング（5〜10 分ごと）を足しても、今の 0.32M CU/日よりずっと安くなります。ただしコードの変更なので、earner による作り直しと審査が必要です。
3. 現状のまま待たせる（月約 25 USD。月の上限 95.2M CU のおよそ半分）。

## 参考（判断は不要）

franken は decision 2026-11-13-morpho3 項目 2 の「見込みの粗利 > ガス代の上限」という送信条件をコードで比べていません。ただし実測の範囲（粗利 20 USD 以上、ガス上限 15 USD）では不等式は成り立っています。次の審査で reviewer が確認します。
