# phase 15c の反映と報告（meta、2026-11-18 03:50Z、run b1c8bda7）

判断 `2026-11-18-lanes-hermes-toga.md` の「meta へ」をすべて入れました。

1. **TOOLS.md**: `relayapi` の後ろに `hermes` の行を追加。relay の行に「fork / scout レーンはユーザーで relay が決める（`--lane` は無関係）、research 700k、`/health` の `cycle`（`alert_85`）」を 1 文で。
2. **scout.md / builder.md**: レーンは relay が決めることを 1 文ずつ。builder.md には「`--lane paper` は paper bot の予算なので自分の読み取りに使わない」も足しました（builder-claude が 11-17 23:44Z に research で hyperevm が引けず、paper レーンで getLogs 約 53 回・eth_call 約 130 回を読んだため）。
3. **earner.md** を先に縮めました（earner は 11-17 以降の実行なし）。サイズ: earner 55995→55918、builder 50240→51089、scout 38116→38862、paper-reviewer 52315→53007（すべて 56000 以下）。
4. **farm-hermes に farmbot から届くか**: 届きます。paper の trial-flatmoney-arbitrum（ユーザー farmbot）のログに `hermes_ok`（publish_lag 1.73 s）。live の bot も同じユーザーなら、Hermes を使う bot の昇格で止まる理由はありません。
5. **lead 248**（TOGA）はすでに builder が `dead_end` にしていました。

## 状況（03:30Z 前後）

- `cycle`: projected_share 0.628、`alert_85` false。
- **live レーン**: 今日 804,706 / 1,500,000 CU（UTC 03:30 で 54%）。live の trial 20 本は自己申告で 1 本約 1 万 CU、合計約 20 万なので、残り約 60 万は ethereum の 3 本（bold-redeem-tail、gearbox-v3-watcher、morpho-nextblock）か、bot の自己カウントの漏れです。bot 別の内訳は meta からは見えません。サイクル平均は live 1 日約 153 万で、毎日ほぼ上限です。上限に達すると live bot は公開ノードに落ちます。bot 別 CU をダッシュボードに出すかどうかは、ご判断ください。
- gate: live 23 本（trial 20/20）、今日の損失 0、capital 1041.7 USD。avalanche の中間ウォレットに 49.86 USD の AVAX が入ったので、trial-aave-avalanche と trial-benqi-avalanche の資金不足（inbox/meta の 2 件）は解消済みです。あとは trial の枠が空くのを待つだけです。
- 14 日間検知も送信もない live bot はありません（いちばん古い gearbox-v3-watcher で 11-12 から 6 日）。

## 判断が要るかもしれないもの（急ぎません）

- **D8X（base）の注文執行手数料**: 誰でも呼べて、1 件 0.10 USDC（24 時間で 159 件、執行者 5 アドレス）。ただし base 版はスポーツ賭けの会場です。builder-claude は S（賭け型の市場）に当たるとして何も作っていません。上限は 1 日 2〜3 USD ほどです。**meta も対象外のままを勧めます**（自分はポジションを持たなくても、賭けの注文の執行で稼ぐことになるため）。違う判断なら `decisions/human/` にお願いします。
