# 引き継ぎ書 18: phase 15j（ダッシュボードとブリーフに live の bot の損益を出す）2026-11-20

本体は `farm/farm-handover.md`。バンドル `farm/phase15j/`（tar sha256 `678cb22b7807ee1784f4115169da6c41be61a9ddf16ab2d89cda0c9a62d75c26`）。状態: **2026-11-20 08:30 JST に人間が適用済み**。

## きっかけ

- 人間（11-20 08:18）: ダッシュボードの realized_today_usd などに利益が出ない
- 原因: 「realized today」は pnl.json の `realized_usd` で、gate が止めた bot を掃き戻したとき（sweep）にだけ書く。live の bot の稼ぎは bot の wallet に残るので、peapods-arb-arbitrum の +1.64 USD などはどこにも出ていなかった

## 変更（farm-dash のテキストパッチ 8 箇所。gate・pnl.json・1 日の損失上限は触らない）

| 項目 | 内容 |
|---|---|
| live の損益（promote から） | bot ごとに「loss since promotion」の符号を逆にしたもの（wallet の今の価値 − gate が入れた額。native は両方とも今の価格なので値動きは消え、稼ぎとガスが残る）。合計・利益の合計・損の合計 |
| live の損益（今日、UTC） | farm-dash のスレッドが 00:00:20 UTC に gate status を 1 回取り（約 900 CU/日）、bot ごとの値を `/var/lib/farmgate/dash-pnl-day.json` に控える。今日の分は今の値 − 控えた値。控えた後に promote された bot は 0 から。farm-dash がその時刻に止まっていたら、その日の最初の表示で控える（「since」に時刻を出す）。日の終わりの合計を 14 日分残す |
| sweep の損益（全期間） | gate.log の sweep の記録の合計 |
| 表示 | タイル「Live PnL」（合計、今日、利益 / 損）。live の表に `pnl_since_promote_usd`・`pnl_today_usd`、`realized_today_usd` は `swept_today_usd` に改名。グラフの見出しを「Swept PnL of stopped bots」に、その下に UTC の日ごとの live の損益 |
| brief.txt | live の各行の末尾に `pnl today`（0 でないとき）。`live PnL since promotion … (gains …, losses …) · today (UTC, since …) … · swept today … · swept all time …` の行、`in profit:` の行。`realized today (UTC)` は `swept today (UTC, gate realized_usd)` に改名 |

- live の損益は gate status の残高（最大 5 分前、brief.txt は 60 秒）から。executor に残った分や、ほかのトークンで持っている分は数えない（watchdog の live-loss stop と同じ見方）
- 止めた bot は live の表から消え、その損益は sweep の側（swept today / all time）に出る。live の「今日」の合計からは外れる
- 「losses」には promote 時の executor 配備のガスが入る（試行は 1 本 0.01〜0.07 USD、ethereum の 3 本は数 USD）

## install.sh

- farm-dash の sha256 を参考値（11-20 08:22 JST に送られた実物）と並べて表示。適用はパッチ（1 回だけ一致）で決める
- オフラインのテスト 9 件（適用前 0/9）。farmgate が `/var/lib/farmgate` に書けることを確認
- バックアップ `.farm-dash.bak-15j`。farm-dash を再起動 → brief.txt に `live PnL since promotion` の行が出るまで待つ。駄目なら戻す。brief の新しい行と、控えたファイルの日・時刻・bot 数を表示

## 適用時の結果（11-20 08:30 JST）

- 適用前の farm-dash は参考値と一致。テスト 0/9 → 9/9。farm-dash は active
- brief.txt: `live PnL since promotion -8.25 USD (gains +2.44, losses -10.69) · today (UTC, since 23:30 UTC) +0.00 · swept today -0.0073 · swept all time -21.4571`、`in profit: trial-peapods-arb-arbitrum +1.63, trial-flatmoney-arbitrum +0.55, trial-metronome-liq-base +0.26`
- 最初の控え: UTC 日 2026-11-19、23:30 UTC から、49 本。00:00:20 UTC にスレッドが 11-19 の分を閉じて 11-20 の控えを取る
- losses −10.69 のうち morpho-nextblock-ethereum 7.14 と bold-redeem-tail-ethereum 2.50 が ethereum の配備ガス（promote 時から分かっている分）。残りは試行の配備ガスと送信のガス

| ファイル | 適用前（期待値 = 実物） | 適用後（期待値 = 実物） |
|---|---|---|
| farm-dash | `bffd08e9fff10f85524bad2a23c62de1b1c774e791ce5457b49ad573eb1585cc` | `b366e5e42a2b8daa3f81549cded0506006d3b406485fafbe000b39a47fab85fe` |
