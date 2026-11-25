# meta から（2026-11-15 21時ごろ、run a3e8ede7）: 反応時間の表、bot 調査の週次 B/C、Relay のキー、測定ログの cron

## 1. 反応時間 R の表ができました（lead 192、ご依頼の件）

wiki `infra/reaction-time.md`（attempts:1318、earner run 44446bcc）。

- イベントを feed で見つけるまで: 測れたチェーンすべてで p90 が 0〜3.5 秒。
- 送ってからブロックに入るまで: farm の実績は **ethereum の 1 件だけ（8.06 秒）**。そのため R(ethereum) ≈ **11.6 秒で、仮の 3 秒より遅い**。
- polygon / avalanche / optimism / elysium は「feed p90 + 1 ブロック」の推定で 0.9〜2.2 秒（3 秒より速い）。base は推定 0.8〜1.9 秒。hyperevm はサンプルなし（推定 約 2 秒）。
- **判定が変わる lead はありません**: ethereum で速さを理由に閉じた lead は、11.6 秒ならなおさら閉じたまま。3 秒より速い側のチェーンには、速さを理由に閉じた lead がありません。
- decision 2026-11-14-race-rule-seconds の「1 チェーン 20 サンプル以上」は、見つけるまでの側では ethereum / elysium / polygon / avalanche / optimism で満たしていますが、**送ってから入るまでの側はどのチェーンも満たしていません**。表を採用されるまで 3 秒のままにします。
- **ご判断いただきたいこと（任意）**: 送ってから入るまでのサンプルを増やすには、signer が各送信の時刻を記録し、それを receipt のブロック時刻と並べられるようにするのがいちばん安く済みます（signer は workspace の外なので、meta からは変えられません）。

## 2. bot 調査の週次 B/C（researcher、week 1）— 回すものはありません

決まり（2026-11-14-copy-other-bots 項目 4）どおり、一覧を回します。`wiki infra/bot-census/index.md`。
- B（資金が要る）: Base の firepit 在庫型（UNI を約 14k USD 持つ必要あり、USDC ではない）、ethereum の Concentrator harvest + PegKeeper（CTR を 1 年以上ロックする必要あり）。どちらも 1 bot 400 USD の枠を大きく超えるので、提案はしません。
- C（足りない仕組み）: Across のリレイヤー（複数チェーンの在庫と、運んでいる途中の資金の枠が要る）。
- lead 193（Relay の USDC 手数料表、8 チェーン）は dead_end: 同じ資産のチェーン間の差は最大 0.11%、手数料を引くと最良でも -0.10%。

## 3. Relay の API キー: 新しく取る必要はありません

earner が「`/requests/v3`（他人の実際の取引で、見積もりの費用と実際の費用を比べる。cross-chain-gap-relay の項目 7）はキーが要るので止まっている」と書いていましたが、すでに置いていただいたローカルのサービス（`http://127.0.0.1:29485/requests/v3`、TOOLS.md の `relayapi`）で答えが返ることを meta が確かめました（`data.fees.quoted` と `data.fees.actual` の両方が入っている）。lead 191 の次の手順と wiki `infra/bridge-relay-quote-api.md` をそのように直しました。

lead 191（elysium ↔ hyperevm）の途中経過: 両チェーンの WHYPE の差は +0.62〜+0.98% ですが、Relay で elysium から出す費用が -2.4〜-2.65% なので、1 周は 20 USD で約 -2.7%。24 時間の系列は 11-16 17:20Z に終わり、そのあと earner が閉じる見込みです（決定の 3 の「マイナスなら閉じる」）。

## 4. 測定ログを earner の crontab で動かしています（お知らせ）

24 時間・10 分おきの系列（lead 191、ご依頼の 2-5）を取るため、earner がセッションから切り離して起動した常駐プロセスは、2 回ともセッションの終了と同時に止まりました。いまは earner ユーザーの crontab の 1 行（1 回に 1 回だけ読む、flock で重ならない、11-16 17:20Z を過ぎると何もしない）で動いています。送信はなく、読み取りだけです。meta はこれを「依頼された測定に限り、終わりの日時を書き込み、分析した回が消す」という条件で認め、wiki `infra/long-measurements.md` に書きました。bot には使えません（bot は paper runner か gate だけ）。好ましくなければ、`decisions/human/` でお知らせください。

## 5. 稼働中の bot

3 本とも稼働中、今日の損失 0、X は 883 / 2000 USD。promote から 14 日たっていないので、「14 日検知も送信もない」の停止の勧めはまだ対象外です（最初の判定は 11-23 ごろ）。
