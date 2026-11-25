# 試行 bot 5 本が live で署名できません（sys.path 欠落）＋ 試行 bot の成績（meta run 7f148f8e, 2026-11-17 03:0xZ）

## 1. 至急：5 本の live 試行 bot は送信できない状態です

- `trial-aave-arbitrum` の live ログ（`bots/live/trial-aave-arbitrum/logs/bot.jsonl`）に、11-16 21:05Z から 11-17 02:47Z まで
  `"No module named 'farmbot_signer'"` の `loop_error` が 31 回あります。nonce は 1（executor 配備のみ）で、送信は 0 件です。
- 原因：live サービスは `/opt/farm/lib` を Python のパスに入れていません。`sys.path.append("/opt/farm/lib")` がないまま
  `import farmbot_signer` している bot は、最初の署名呼び出しで必ず失敗します。paper では signer を import しないので、
  paper ログ・fork 証明・審査のどれにも出ません。
- 同じ書き方（パス行なし）の live bot：**trial-aave-arbitrum, trial-aave4-base, trial-cv3-buy-base, trial-morpho-cbbtc-base,
  trial-revert-lend-arbitrum**。aave-arbitrum 以外はまだ機会に当たっていないのでエラーが出ていないだけです。
  パス行のある bold-redeem-tail-ethereum と HAI の optimism 試行 3 本は正常に署名・送信しています。
- 損失はありません（送れないだけ）。live コピーは meta には書けません。選択肢：
  (a) bold の時と同様に、各 `bot.py` の先頭近く（`import sys` の後）に `sys.path.append("/opt/farm/lib")` を 1 行足して
  `gate restart <id>`（executor・wallet・manifest はそのまま）。
  (b) `gate stop` して builder に直させ、再審査・再 promote（executor 再配備の費用がかかります）。
  meta の推奨は (a) です。修正が 1 行で、HAI 3 本が同じ行で動いている実績があります。
- 再発防止（今回の変更）：`tools/manifest-check.py` が、パス行なしの `import farmbot_signer` を **ERROR** にします
  （上の 5 本と paper の trial-morpho-eth-base で検出、パス行のある 5 本は OK）。builder.md と paper-reviewer.md に 1 行ずつ、
  wiki `pitfalls/signer-import-path.md` を追加しました。

## 2. 試行 bot ごとの成績（live 分のみ、ログより）

| bot | live 開始 (UTC) | 送信 | 勝ち | ガス (L2 実行分, USD) | 負けの理由 |
|---|---|---|---|---|---|
| trial-oraclejob-hai-optimism | 11-16 22:06 | 20 | 0 | 0.15 | 全件 due と同じブロックに着地（遅れ 0 秒）。相手の priority fee が高い 18 件、こちらが同等以上なのに負け 11 件、送信前に他者が更新済み（late）11 窓 |
| trial-oraclebatch-hai-optimism | 11-17 01:18 | 3 | 0 | 0.02 | 3 件とも同じブロック、相手 0.19 / 0.17 gwei に対しこちら 0.10 / 0.056 gwei（入札不足） |
| trial-updaterate-hai-optimism | 11-16 18:54 | 6 | 0 | 0.004 | 6 件中 5 件は同じブロック、2 件は 2 秒遅れ。相手の入札が高い 5 窓、こちらが上なのに負け 3 窓 |
| trial-aave-arbitrum | 11-16 20:50 | 0 | 0 | 0 | 上記 1 の import エラーで送信不能 |
| trial-revert-lend-arbitrum | 11-16 23:44 | 0 | 0 | 0 | 機会なし（同じ import 問題あり） |
| trial-cv3-buy-base | 11-17 01:17 | 0 | 0 | 0 | 機会なし（reserve 0.0006 USD）。同じ import 問題あり |
| trial-morpho-cbbtc-base | 11-17 02:52 | 0 | 0 | 0 | 開始直後。同じ import 問題あり |
| trial-aave4-base | 11-17 02:54 | 0 | 0 | 0 | 開始直後。同じ import 問題あり |

- 合計：送信 29 件、勝ち 0、純損益はガス分のみ（L2 実行ガス約 0.17 USD、L1 データ費は別）。gate の当日損失は 0。
- 注目点：HAI 試行で「こちらの priority fee が勝者以上なのに同じブロックで負けた」ケースが 14 件あります。OP Stack の
  sequencer が単純な priority fee 順で並べていない（到着順や別経路）可能性があります。入札を上げても勝てない根拠になり得るので、
  builder が次に調べるべき点です（勝者 tx の index とこちらの index の比較）。
- 11-24 までに勝ちが出るかについて：optimism の 3 本は入札上限（gross > ガス上限 の条件）で勝者の入札に届かない窓がほとんどです。
  import 修正後の 5 本（arbitrum / base の清算・買い取り）が実質的な判断材料になります。

## 3. その他

- `trial-morpho-eth-base`（paper）の Base 資金不足の件は reviewer が別ノートで報告済み。同 bot も import 問題があり、
  manifest-check が ERROR を出すので次の審査で `fix` になります。資金を入れる前に直ります。
- gearbox-v3-watcher-ethereum：live 11-09 17:44Z から送信 0（nonce 1）。14 日無送信の停止推奨基準には 11-23 に達します。
- researcher 8 回/日：変更は 11-17 から。比較できる件数がまだないので、次回以降に前後の leads 数と重複率を報告します。
- 審査ノイズ対策（11-17 のご依頼 1〜3）は paper-reviewer.md に反映済み：`executor armed` は setup tx がある bot だけ要求、
  開始行に executor アドレスがない場合は inbox/meta へ（アドレス違いのみ inbox/human）、資金待ちの `wait` は +2 時間で再審査、
  review.md は新しい判断を先頭に・`gate promote` の前に書く。manifest-check に「start ログ行に executor アドレスなし」の警告を追加
  （報告のあった 3 本で検出、記録している 7 本は検出なし）。
