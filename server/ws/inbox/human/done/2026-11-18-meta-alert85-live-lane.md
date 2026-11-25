# Alchemy サイクルの `alert_85` が true になりました／live レーンが毎朝尽きています（meta、2026-11-18 09:35Z、run 60cda4b4）

判断 `2026-11-18-lanes-hermes-toga.md` 1 と `2026-11-18-trial-slots-30.md` 3 に従った報告です。

## 1. `/health` の `cycle`（09:30Z）

- `cu` 33,637,880 / `allowance` 95,200,000、`projected_share` 1.138、**`alert_85` true**（03:30Z は 0.628、false）。
- `pace_cu_per_day` 5,926,670、`projected_cu_recent` 108.4M。今日の 9.5 時間の合計 2.31M（live 1,615,120、research 270,410、fork 208,140、scout 199,398、watch 10,770、paper 8,860）を 24 時間に伸ばした数字です。
- **meta の見立て: 11-24 より前に尽きる見込みはありません。12-01 までに尽きる見込みも小さいです。** 理由: live はもう日の上限（1.5M）に達しているので、今日の残りは伸びません。各レーンの日の上限の合計は live 1.5M + paper 0.9M + research 0.7M + fork 0.6M + scout 0.3M + watch 0.3M = 4.3M/日。残り 12.6 日 × 4.3M = 54.2M で、サイクルの残り 61.56M に届きません（farm-feed の 0.7M/日を足すと 63M でほぼ同じになり、全レーンが毎日上限まで使えば 11-30〜12-01 ごろ）。サイクル平均は 2.18M/日です。`projected_cu_recent` はレーンの上限を考えない直線の伸ばし方なので、live の上限が当たる朝ほど高く出ます。
- 尽きる日を早めるとすれば、レーンの上限を上げたとき（または feed の増加）です。上げるときはこの計算をやり直してください。

## 2. 本当の問題: live レーンが毎朝 08:40Z ごろに尽きる

- live: 03:30Z に 804,706、09:30Z に 1,615,120（6 時間で 810k、約 135k/時 = 約 3.2M/日の需要）。上限 1.5M には **08:40Z ごろ**に達し、その後は UTC の日が変わるまで、live の bot 33 本と watchdog の読み取りが公開ノードに落ちます（1 日の約 6 割の時間）。
- trial bot 30 本の目的は「送って勝率を測る」ことなので、公開ノードの遅れや空の返事（`pitfalls/research-lane-spent-public-fallback.md`）が勝率の数字に混ざります。11-24 の判断で trial の結果を読むときは、この時間帯を割り引いてください。
- 案（どれか 1 つ）: (a) live の日の上限を 3.5M 前後に上げる（上の計算では 12-01 までに尽きる側になるので、代わりに paper 0.9M（今日 8,860 しか使っていない）を 0.2M に下げる）。(b) 上限はそのままで、bot ごとの CU を `/health` かダッシュボードに出し、使いすぎの bot を reviewer が `fix` に回す。meta は (a) の付け替え（paper 枠 → live）を勧めます。合計の上限が変わらないので、サイクルの計算は同じです。

## 3. trial の状況（gate status 09:2xZ）

- live 33 本（trial 30/30、上限に達しています）、今日の損失 0、capital 1043.07 USD。
- trial 30 本の nonce はすべて 1（executor のデプロイだけで、**送信 0 件**）。morpho-nextblock-ethereum だけ nonce 2。
- live ログの `simulate_revert`: trial-moonwell-base 12 件（同じ 0xeeddaac5…0e で、同じ借り手に何度も）、trial-morpho-whype-hyperevm 7 件（"position is healthy"、比率 0.99999 の境目）、trial-morpho-arbitrum 2 件（arithmetic underflow）。どれも eth_call の段階で止まり、ガスは使っていません。moonwell の繰り返しは builder か reviewer が見る項目です。
- 14 日間、検知も送信もない live bot はまだありません（いちばん古い gearbox-v3-watcher-ethereum が 11-23 前後に 14 日に届きます）。

## 4. 反映済み

- 判断 `2026-11-18-trial-slots-30.md` 5: paper-reviewer.md と builder.md の上限を 30 本にし、4（清算以外の型を先に promote）を paper-reviewer.md に 1 句で入れました。サイズ: paper-reviewer 53,068、builder 51,292（どちらも 56,000 以下）。
