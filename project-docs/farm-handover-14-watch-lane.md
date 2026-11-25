# 引き継ぎ書 14: phase 15e（watchdog を live レーンから外す）と 15f（bsc の公開ノード）2026-11-18〜19

本体は `farm/farm-handover.md`。バンドル `farm/phase15e/`（tar sha256 `3ad72e710fd43a6334a12bf2df29f9d92f50be13e38be29b76e7616516a666a6`、`regress-15c.py` は 15c の test-15c.py の写し）と `farm/phase15f/`（tar sha256 `787c867a0e47fa74d944a7a62801ca44cb18c0dd0b3fc731b4db0154646f996e`）。状態: **15e は 2026-11-18 12:50 JST（03:49 UTC）、15f は 2026-11-19 01:13 JST に人間が適用済み**。

## きっかけ（11-18 12:35 JST のブリーフ）

- live の試行が 20 本になり live bot は 23 本。live レーンの Alchemy CU が 03:35 UTC で 882k（1 日約 600 万のペース。サイクル平均は 1 日約 153 万）
- 中身の大半は farm-watchdog: 15 秒ごとに全 live bot の nonce（20 CU）、60 秒ごとに残高・USDC・価格（10i）を live レーン（Alchemy 優先、予算なし）で読む → 1 本あたり約 18 万 CU/日、23 本で約 400 万 CU/日。bot の数に比例して増える
- このペースだと Alchemy の月の枠（95.2M）は 12-01 の前（11-28〜29 ごろ）に尽きる。尽きると送信（Alchemy のみ）が全部止まる。ダッシュボードと `/health` の見込み（約 60M）はサイクル平均で計算していて、この急増を拾えていなかった
- meta は「live レーンが 150 万の上限に達すると公開ノードに落ちる」と書いたが誤り（live は予算で絞らない。だから月の枠を食い続ける）。11-18 18:43 に訂正メモを配置、meta は TOOLS.md を直した

## 変更（15e）

| 対象 | 内容 |
|---|---|
| rpc-relay（2 箇所） | レーン `watch`（公開ノード先、Alchemy は予算の内だけ。誰でも名乗れる）。`/health` の `cycle` に `pace_cu_per_day`（今日の分を 1 日に換算、2 時間たってから。昨日と比べて大きいほう）と `projected_cu_recent`。`projected_share` と `alert_85` は 2 つの見込みの大きいほうで判定 |
| farm-watchdog（1 箇所） | `?lane=live` → `?lane=watch`。確認の中身と間隔（15 秒・60 秒）は変えない |
| relay.json | `alchemy_daily_cu.watch` 300,000（新規）、`fork` 400,000 → 600,000（11-18 は 03:35 UTC で 82k、1 日約 55 万のペース） |

- watchdog の読み取りが公開ノードの遅れで古い値になっても、鍵の漏洩の誤検知にはならない（nonce は実際より大きくならない）。読めなければ READ_FAILED でそのチェーンを飛ばし、次の回にまた読む
- gate-ctl（promote の残高確認、15b の待ち）は live レーンのまま
- ダッシュボード（farm-dash）の「on course for」はサイクル平均のまま。急増は `/health` の `projected_cu_recent` で見る
- **`alert_85` は 11-19 いっぱい true のまま出る見込み（誤報）**: 「今日の換算」と「昨日」の大きいほうを使うため、15e 前の高いペース（11-18 は 1 日換算 756 万）が 11-19 の「昨日」として残る。11-20 から実際のペースに戻る

## install.sh（15e）

- 参考値: rpc-relay 15c 版 `323337d8…9581006c`、farm-watchdog 12d 版 `4f692e41…5ea13f9`。適用はテキストパッチ（1 回だけ一致）で決める
- オフラインのテスト 5 件（適用前 1/5）と、15c のテスト 7 件を新しい relay で
- relay を再起動 → `/health` に watch と `pace_cu_per_day` → watchdog を再起動 → 45 秒後に active、journal の末尾と `read failed` の数を表示 → 約 60 秒の live レーンの増え方を表示。relay か watchdog が戻らなければ、両方と relay.json を元に戻す
- バックアップ: `.rpc-relay.bak-15e`、`.farm-watchdog.bak-15e`、`relay.json.bak-15e`

## 15e 適用時の結果（12:50 JST）

- 適用前の sha256 は 15c・12d の版と一致。テスト 1/5 → 5/5、15c の回帰 7/7
- relay・signer・feed・watchdog は active、watchdog の `read failed` 0 件
- live レーンの増え方: 適用中の約 60 秒で +926 CU（15e 前は 1 分約 4,000）。その後の実測では、live bot 本体の分だけで 1 日約 290 万（33 本）〜370 万（34 本）。watch レーンの Alchemy は 1 日 4 万程度
- その時点の cycle: 32.53M、平均の見込み 60.09M、最近のペースの見込み 129.6M（15e 前のペースを含む）、alert_85 true

| ファイル | 適用前（期待値 = 実物） | 適用後（期待値 = 実物） |
|---|---|---|
| rpc-relay | `323337d8ffe6a46a7ca759101b1f8c823521332a5f990c2448d075fe9581006c` | `89f94742647ba2e998e9a7286e8a80f30c9c32a0eedf08d75eb73f1a55d9bbfd` |
| farm-watchdog | `4f692e414c9825168d879e15e4455725536038d48946d02bce5e8fcbe5ea13f9` | `848dafb03609211d8c194dcb9c259973f8f4b9d12201f6ecfb9c9dd5938b00b1` |
| relay.json | `5aa7b48b…9509efab`（15c） | `7b4313a3cd543dd06c119f1023062b4cd5809ea457ec66ef15c5acb4788d2382` |

## 15f: relay の bsc に 2 つ目の公開ノード（11-19、人間の判断）

- きっかけ: meta（11-18 15:45Z）。scout レーンの Alchemy の枠を使い切った 12:57〜13:15Z、bsc の全読み取りが `all providers failed: no provider available`。relay の bsc の公開ノードは `bsc-dataseed.bnbchain.org` だけで、eth_getLogs を出さない。scout が relay を迂回して `bsc-dataseed.binance.org` に直接 curl した（meta は TOOLS.md で禁止を明記済み）
- 変更: relay.json `chains.bsc.public` の先頭に `https://bsc-dataseed.binance.org`（scout の実測で eth_getLogs 2 万ブロック/ページ可）、その後ろに今までの bnbchain.org。ほかは変えない。meta 宛てメモ `inbox/meta/2026-11-19-phase15f-bsc-public.md`
- install: 直接 `eth_chainId` が 0x38、getLogs を 1 回 → relay.json を置いて relay を再起動 → harness から relay 経由で bsc の `eth_blockNumber` → signer・watchdog・feed が active。駄目なら relay.json を戻す。バックアップ `relay.json.bak-15f`
- live の bsc bot（aave-bsc・flux-bsc・venus-bsc）は live レーン（Alchemy）なので影響なし
- 同じ判断で、試行 30/30 の間も paper-reviewer の間隔は変えない（枠が空いたらすぐ埋めるため）

## 15f 適用時の結果（11-19 01:13 JST）

- relay.json は 15e 後の版と一致。binance.org の chain id 0x38
- install の getLogs の確認は、件数の多い USDT の 2,000 ブロックを選んだため `-32005 limit exceeded`（結果の大きさの制限）。getLogs が使えること自体は scout の少ない件数での実測による。確認の対象の選び方の誤り
- relay 経由の bsc の eth_blockNumber ok、relay・signer・watchdog・feed は active
- **注意**: relay は `-32005` をレート制限として扱い、そのノードを 10 秒休ませる。大きな getLogs を投げると、その間 bsc の公開ノードの先頭が使えない。メモどおり、ページに分けて読ませる

| ファイル | 適用前（期待値 = 実物） | 適用後（期待値 = 実物） |
|---|---|---|
| relay.json | `7b4313a3cd543dd06c119f1023062b4cd5809ea457ec66ef15c5acb4788d2382`（15e） | `ba248582d9d64c03c5a9cb04b0d70be598aeec52756bde26365e09016fc9c9b3` |
