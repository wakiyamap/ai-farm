# meta 6e5f9489（2026-11-16 03:0xZ）: earner の空回り、sources.d の 4 件、elysium からの公式ブリッジ出金、Relay 項目 7 の結果

## 1. earner がずっと空回りしています（提案あり）

- 11-16 00:00〜02:34Z の earner は 17 回。そのうち 15 回は対象なしでした（`no_target` 10 回、「no target taken」と書いて `dead_end_recorded` が 5 回）。11-15 も 87 回中、後半はほぼ同じ状態です。対象があったのは lead 197（Moonwell）と bold-redeem-tail の修正 1 回だけです。
- KB の `attempts` も、11-15 20:27Z 以降の 41 行のうち 20 行（1346〜1379 の「queue walk #N」「exhaustion check #N」）が、空の待ち行列を確認しただけの行でした。
- meta の変更（今回）: earner.md の「No target left」の項に「待ち行列の確認だけの attempts 行は書かない。測った新しい区画だけ、その名前で 1 行」と足しました（組み立て後 55,372 → 55,533 bytes、上限 56,000 以内）。次の meta で、この種の行の割合（今 20/41 = 49%）を数えます。
- **提案（人間の判断が必要）**: 板が空のとき（unmeasured の lead なし、`decision: fix` の paper bot なし、新しい review・decision なし）は、harness が earner の起動を間引く（例: 1 時間に 1 回）。今は 1 回あたり数分〜数十分のトークンを、ほぼ同じ確認の繰り返しに使っています。起動の頻度は meta が変えられないので、お願いします。

## 2. ledger/sources.d が 40/40 です（外す 4 件、移動をお願いします）

decision 2026-11-15-whype-gap-review-points の 3 の条件で確かめました（measured の lead が残っていない、live・paper の bot が根拠にしていない。`bots/` を grep して該当なし）。

| source | lead | 状態 |
|---|---|---|
| `inverse_dbr_auction.buy` | attempts 1372 | dead_end（区画全体で 1 日約 3 USD） |
| `grvt.swapped_receipt_in` | 190 | dead_end |
| `angle_transmuter.swap` | 195 | dead_end |
| `convex_locker.kick_reward` | 179 | dead_end |

外さないもの: `felix_cdp.redemption`（lead 149 の再開判定に earner が使っている）、`frankencoin.challenge_started`（live の franken-dutch-ethereum の元の lead 74）、`curve_pegkeeper.*`（lead 16 が measured）。

meta のセッションでは `ledger/sources.d` の中の `mv` / `rm` が今回も拒否されました。上の 4 ファイルを `ledger/sources-retired/` へ移していただくか、meta にその移動の権限をください。急ぎではありません（今、追加待ちの source はありません）。

## 3. elysium の中間ウォレットから 199.96 USDC が公式ブリッジで出ています（確認のみ）

- `gate status` の capital が 883.92 USD（00:3xZ）→ 683.62 USD（02:4xZ）に下がりました。原因は 2026-11-16 01:59:04Z の elysium の tx `0x99e43ee6874a61522238ce95928f22729710b409caefd9d0bb0137f8a9c3a101`（中間ウォレット `0x915bd260…` の nonce 0、gateway router `0x61ebbc3a…` の `outboundTransfer`、宛先は同じ中間ウォレット、HyperEVM 側トークン `0xb88339cb…`）。人間による出金と理解しています。
- 公式ブリッジの待ちは HyperEVM の 483,840 ブロック（約 5.6 日、lead 191 の測定）なので、届くのは **11-21〜22 ごろ**です。そのあと HyperEVM の Outbox で claim の tx が必要です（誰でも出せる、ガスは 0.03 USD 未満）。
- その間、この 200 USD は `gate status` の capital に数えられません（X 2000 に対しては余裕があるので問題はありません）。人間が出したものでなければ教えてください。

## 4. Relay の項目 7（見積もりと実際の支払い）と lead 191 (a) は答えが出ています

- 見積もりは正直です: 第三者の Relay 2,610 件で、見積もりの手数料合計から 0.01 USD 超ずれたのは 7.5%（p99 0.46 USD）。elysium の経路は全件 0.03 USD 以内（attempts 1342）。
- elysium から出る費用は見積もりの中にあり、中央値 −3.91%（WHYPE→HYPE、29 件）。入るのはほぼ無料（+0.14%）。プールの差 約 1% は Relay 経由では取れません。
- 公式ブリッジはガスだけ（両側合わせて 0.007〜0.03 USD）、1:1、待ち 約 5.6 日、claim は誰でも可（attempts 1348、wiki `infra/elysium-official-bridge.md`）。
- 人間の 205 USDC（ethereum → elysium、11-15）の request は、`user=` / `recipient=` では見つかりませんでした。request id か elysium 側の tx hash をいただければ `/intents/status` で引けます。
- (b)（7 日の待ちとの比較）は、logger の記録が 17:20Z に終わったあとの分析で答えます。そのあと crontab の削除と `crontab -l` が空であることを報告します。

## 5. その他

- 反応時間: decision 2026-11-16-reaction-time を wiki `infra/reaction-time.md` の先頭に反映しました（ethereum 12 秒、ほかは 3 秒）。ethereum ではブロックが 12 秒なので、3 秒でも 12 秒でも L は同じ次のブロックになり、判定が変わる lead はありません（decision の 4）。
- live 3 本はすべて稼働、今日の損失 0。14 日間検知も送信もない bot の確認は 11-23 からです。
